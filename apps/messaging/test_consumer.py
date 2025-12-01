import json
from channels.generic.websocket import AsyncWebsocketConsumer

class SimpleTestConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return
        
        await self.accept()
        await self.send(json.dumps({
            "type": "connection_established",
            "message": "Simple test connection successful",
            "user_id": user.id
        }))
    
    async def disconnect(self, close_code):
        pass
    
    async def receive(self, text_data=None):
        if text_data:
            await self.send(json.dumps({
                "type": "echo",
                "message": f"Echo: {text_data}"
            }))
