# toxicity_app/consumers.py
import json
import pickle
import os
from pathlib import Path
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .models import Report

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        self.model, self.vectorizer = await self.load_models()
        
        if self.model is None or self.vectorizer is None:
            print("Warning: Model file not found. Make sure to train the model first.")
        
        await self.accept()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    @sync_to_async
    def load_models(self):
        """Load both the SVM model and TF-IDF vectorizer"""
        try:
            base_dir = Path(__file__).resolve().parent.parent
            
            model_path = os.path.join(base_dir, 'toxicity_app', 'ml_models', 'svm_model.pkl')
            vectorizer_path = os.path.join(base_dir, 'toxicity_app', 'ml_models', 'tfidf_vectorizer.pkl')
            
            print(f"Looking for model at: {model_path}")
            print(f"Looking for vectorizer at: {vectorizer_path}")
            print(f"Model file exists: {os.path.exists(model_path)}")
            print(f"Vectorizer file exists: {os.path.exists(vectorizer_path)}")
            
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
            
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
            text_vectorized = self.vectorizer.transform([text])
            prediction = self.model.predict(text_vectorized)
            return bool(prediction[0])
        except Exception as e:
            print(f"Error during prediction: {e}")
            return False
    
    @sync_to_async
    def save_report(self, message_text, report_type, reporter_username, reported_username):
        """Save a report to the database"""
        try:
            report = Report(
                message_text=message_text,
                report_type=int(report_type),
                reporter_username=reporter_username,
                reported_username=reported_username
            )
            report.save()
            print(f"Report saved successfully: {report}")
            return True
        except Exception as e:
            print(f"Error saving report: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        
        # Check if it's a report message
        if data.get('type') == 'report':
            message_id = data.get('message_id')
            message_text = data.get('message_text')
            report_type = data.get('report_type')
            reporter_username = data.get('reporter_username')
            reported_username = data.get('reported_username', 'Unknown')  # Get reported username if available
            
            # Save the report to the database
            success = await self.save_report(message_text, report_type, reporter_username, reported_username)
            
            # Send confirmation to the reporter
            await self.send(text_data=json.dumps({
                'type': 'report_confirmation',
                'success': success,
                'message': "Report submitted successfully" if success else "Failed to submit report"
            }))
        else:
            # Handle regular chat message
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