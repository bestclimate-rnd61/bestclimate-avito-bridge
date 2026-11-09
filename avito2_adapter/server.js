"use strict";
const http = require("node:http");
const crypto = require("node:crypto");
const {parseAvitoChats} = require("./inbox");

const port = Number(process.env.PORT || 10000);
const base = "https://api.avito.ru";
const id = process.env.AVITO2_CLIENT_ID || "";
const secret = process.env.AVITO2_CLIENT_SECRET || "";
const writeEnabled = (process.env.AVITO2_WRITE_ENABLED || "").toLowerCase() === "true";
const bridgeSecret = process.env.BRIDGE_SECRET || "";
let status = { configured: Boolean(id && secret), auth: "not_checked", checkedAt: null };

async function probe() {
  if (!id || !secret) {
    status = { configured: false, auth: "missing_credentials", checkedAt: new Date().toISOString() };
    return;
  }
  try {
    const body = new URLSearchParams({grant_type:"client_credentials",client_id:id,client_secret:secret});
    const resp = await fetch(base + "/token", {method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},body,signal:AbortSignal.timeout(10000)});
    if (!resp.ok) {
      status = {configured:true,auth:"rejected",checkedAt:new Date().toISOString(),httpStatus:resp.status};
      return;
    }
    const json = await resp.json();
    if (!json.access_token) throw new Error("no token");
    const account = await fetch(base + "/core/v1/accounts/self", {headers:{Authorization:"Bearer " + json.access_token},signal:AbortSignal.timeout(10000)});
    status = {configured:true,auth: account.ok ? "verified" : "account_check_failed",checkedAt:new Date().toISOString(),httpStatus:account.status};
    // Never log, persist, or return access tokens, account identifiers, or personal data.
  } catch (_) {
    status = {configured:true,auth:"connection_error",checkedAt:new Date().toISOString()};
  }
}
function authorized(req) {
  const supplied = req.headers["x-bridge-secret"] || (req.headers.authorization || "").replace(/^Bearer /i, "");
  if (!bridgeSecret || typeof supplied !== "string") return false;
  const a = Buffer.from(supplied), b = Buffer.from(bridgeSecret);
  return a.length === b.length && crypto.timingSafeEqual(a,b);
}
async function readInbox(req,res) {
  if (!authorized(req)) { res.writeHead(401); return res.end(); }
  if (!id || !secret) { res.writeHead(503); return res.end(JSON.stringify({error:"credentials_not_configured"})); }
  try {
    const tokenResponse = await fetch(base + "/token", {
      method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},
      body:new URLSearchParams({grant_type:"client_credentials",client_id:id,client_secret:secret}),
      signal:AbortSignal.timeout(10000)
    });
    if (!tokenResponse.ok) {res.writeHead(502);return res.end(JSON.stringify({error:"avito_auth_failed"}));}
    const token=(await tokenResponse.json()).access_token;
    if (!token) throw new Error("missing_token");
    const accountResponse=await fetch(base+"/core/v1/accounts/self",{
      headers:{Authorization:"Bearer "+token},signal:AbortSignal.timeout(10000)
    });
    if (!accountResponse.ok) {res.writeHead(502);return res.end(JSON.stringify({error:"account_lookup_failed"}));}
    const account=await accountResponse.json();
    const userId=account.id;
    if (!Number.isSafeInteger(Number(userId)) || Number(userId)<=0) throw new Error("invalid_account_id");
    const url=base+"/messenger/v2/accounts/"+encodeURIComponent(String(userId))+"/chats?limit=25";
    const chatsResponse=await fetch(url,{headers:{Authorization:"Bearer "+token},signal:AbortSignal.timeout(10000)});
    if (!chatsResponse.ok) {res.writeHead(502);return res.end(JSON.stringify({error:"messenger_unavailable",upstreamStatus:chatsResponse.status}));}
    const parsed=parseAvitoChats(await chatsResponse.json());
    res.writeHead(200,{"Content-Type":"application/json","Cache-Control":"no-store"});
    return res.end(JSON.stringify(parsed));
  } catch (_) {res.writeHead(502,{"Content-Type":"application/json"});return res.end(JSON.stringify({error:"upstream_connection_error"}));}
}
http.createServer((req,res)=>{
  if (req.method === "GET" && req.url === "/avito/inbox") return void readInbox(req,res);
  if (req.method !== "GET" || !["/","/health"].includes(req.url)) {
    res.writeHead(404,{"Content-Type":"application/json"}); return res.end('{"error":"not_found"}');
  }
  res.writeHead(200,{"Content-Type":"application/json","Cache-Control":"no-store"});
  res.end(JSON.stringify({service:"avito2-readonly",writeEnabled:false,configured:status.configured,auth:status.auth,checkedAt:status.checkedAt}));
}).listen(port,"0.0.0.0",()=>{
  if(writeEnabled) console.error("AVITO2_WRITE_ENABLED must remain false; write endpoints are not implemented");
  void probe();
});
