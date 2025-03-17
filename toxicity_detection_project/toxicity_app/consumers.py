# toxicity_app/consumers.py
import json
import pickle
import os
from pathlib import Path
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # Load the pre-trained models
        self.model, self.vectorizer = await self.load_models()
        
        # Print warning only if models couldn't be loaded
        if self.model is None or self.vectorizer is None:
            print("Warning: Model file not found. Make sure to train the model first.")
        
        await self.accept()
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    @sync_to_async
    def load_models(self):
        """Load both the SVM model and TF-IDF vectorizer"""
        try:
            # Get the absolute path to the base directory
            # This should point to the project root directory
            base_dir = Path(__file__).resolve().parent.parent
            
            # Construct absolute paths to the model files
            model_path = os.path.join(base_dir, 'toxicity_app', 'ml_models', 'svm_model.pkl')
            vectorizer_path = os.path.join(base_dir, 'toxicity_app', 'ml_models', 'tfidf_vectorizer.pkl')
            
            # Debug information
            print(f"Looking for model at: {model_path}")
            print(f"Looking for vectorizer at: {vectorizer_path}")
            print(f"Model file exists: {os.path.exists(model_path)}")
            print(f"Vectorizer file exists: {os.path.exists(vectorizer_path)}")
            
            # Load SVM model
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
            
            # Load TF-IDF vectorizer
            with open(vectorizer_path, 'rb') as f:
                vectorizer = pickle.load(f)
            
            print("Models loaded successfully!")
            return model, vectorizer
        except FileNotFoundError as e:
            print(f"Error loading models: {e}")
            return None, None
        except Exception as e:
            print(f"Unexpected error loading models: {e}")
            import traceback
            traceback.print_exc()
            return None, None
    
    @sync_to_async
    def is_toxic(self, text):
        """Predict if the message is toxic using the pre-trained model and vectorizer"""
        if self.model is None or self.vectorizer is None:
            return False  # Default to non-toxic if models aren't loaded
        
        try:
            # Transform the text using the vectorizer
            text_vectorized = self.vectorizer.transform([text])
            
            # Predict using the SVM model
            prediction = self.model.predict(text_vectorized)
            
            # Return True if toxic, False otherwise
            return bool(prediction[0])
        except Exception as e:
            print(f"Error during prediction: {e}")
            return False
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        username = data['username']
        message = data['message']
        
        # Check if message is toxic
        is_toxic = await self.is_toxic(message)
        
        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'username': username,
                'message': message,
                'is_toxic': is_toxic
            }
        )
    
    async def chat_message(self, event):
        username = event['username']
        message = event['message']
        is_toxic = event['is_toxic']
        
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'username': username,
            'message': message,
            'is_toxic': is_toxic,
            'warning': "Warning: Toxic content detected!" if is_toxic else ""
        }))