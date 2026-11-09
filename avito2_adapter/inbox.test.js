"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const {parseAvitoChats}=require("./inbox");
test("missing chats returns empty list",()=>assert.deepEqual(parseAvitoChats({}),{count:0,chats:[]}));
test("normalizes and bounds message",()=>{
 const r=parseAvitoChats({chats:[{id:"c1",item_id:42,unread_count:2,last_message:{content:{text:"a".repeat(2500)}}}]});
 assert.equal(r.chats[0].lastMessage.length,2000);assert.equal(r.chats[0].itemId,"42");
});
test("ignores unknown profile fields",()=>{
 const r=parseAvitoChats({chats:[{id:"c1",buyer:{phone:"private"}}]});
 assert.equal(JSON.stringify(r).includes("private"),false);
});
