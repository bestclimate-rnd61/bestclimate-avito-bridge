"use strict";
function parseAvitoChats(payload) {
 const chats=Array.isArray(payload?.chats)?payload.chats:[];
 return {count:chats.length,chats:chats.slice(0,25).map(chat=>({
   chatId:String(chat.id || ""), itemId:chat.item_id == null ? null:String(chat.item_id),
   updatedAt:chat.updated || null, unreadCount:Number(chat.unread_count || 0),
   lastMessage:typeof chat.last_message?.content?.text==="string"
      ? chat.last_message.content.text.slice(0,2000):null
 }))};
}
module.exports={parseAvitoChats};
