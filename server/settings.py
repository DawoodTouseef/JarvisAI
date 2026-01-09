from dotenv import load_dotenv


from mongita import MongitaClientDisk
import json
import os
from typing import Dict, Any

class SettingsManager:
    def __init__(self, db_path: str = "./db"):
        # Create the database directory if it doesn't exist
        os.makedirs(db_path, exist_ok=True)
        self.client = MongitaClientDisk(db_path)
        self.db = self.client.settings_db
        self.settings_collection = self.db.settings
        
        # Initialize default settings if collection is empty
        if self.settings_collection.count_documents({}) == 0:
            self.initialize_default_settings()
    
    def initialize_default_settings(self):
        """Initialize default settings in the database"""
        default_settings = {
            "useVideo": True,
            "theme": "dark",
            "notifications": True,
            "auto_update": False,
            "city": "New York",
            "use24hrFormat": False,
            "useFaceRecognition": False,
            "faceRecognitionModels": [],
            "events": []
        }
        self.settings_collection.insert_one(default_settings)
    
    def get_settings(self) -> Dict[str, Any]:
        """Retrieve all settings from the database"""
        settings_doc = self.settings_collection.find_one({})
        if settings_doc:
            # Remove the _id field from the result
            settings_doc.pop('_id', None)
            return settings_doc
        else:
            # Return default settings if none exist
            return {
                "useVideo": True,
                "theme": "dark",
                "notifications": True,
                "auto_update": False,
                "city": "New York",
                "use24hrFormat": False,
                "useFaceRecognition": False,
                "faceRecognitionModels": [],
                "events": []
            }
    
    def update_settings(self, new_settings: Dict[str, Any]) -> bool:
        """Update settings in the database"""
        try:
            # Get the first document (there should only be one settings doc)
            existing_doc = self.settings_collection.find_one({})
            
            if existing_doc:
                # Update the existing document
                result = self.settings_collection.update_one(
                    {"_id": existing_doc["_id"]},
                    {"$set": new_settings}
                )
                return result.modified_count > 0
            else:
                # Insert new settings document
                self.settings_collection.insert_one(new_settings)
                return True
        except Exception as e:
            print(f"Error updating settings: {e}")
            return False
    
    def get_events(self) -> list:
        """Retrieve all events from the database"""
        settings_doc = self.settings_collection.find_one({})
        if settings_doc and 'events' in settings_doc:
            return settings_doc['events']
        else:
            return []
    
    def save_event(self, event_data: Dict[str, Any]) -> bool:
        """Save a new event to the database"""
        try:
            # Get the existing document
            existing_doc = self.settings_collection.find_one({})
            
            if existing_doc:
                # Get current events and append the new one
                current_events = existing_doc.get('events', [])
                
                # If the event has a dateTime field, use it; otherwise use the old time field
                processed_event_data = event_data.copy()
                if 'dateTime' in event_data:
                    processed_event_data['time'] = event_data['dateTime']
                    del processed_event_data['dateTime']
                
                current_events.append(processed_event_data)
                
                # Update the events array in the document
                result = self.settings_collection.update_one(
                    {"_id": existing_doc["_id"]},
                    {"$set": {"events": current_events}}
                )
                return result.modified_count >= 0  # Success if no error occurred
            
            else:
                # Create new settings document with the event
                self.settings_collection.insert_one({"events": [event_data]})
                return True
        except Exception as e:
            print(f"Error saving event: {e}")
            return False
    
    def update_event(self, event_data: Dict[str, Any]) -> bool:
        """Update an existing event in the database"""
        try:
            # Get the existing document
            existing_doc = self.settings_collection.find_one({})
            
            if existing_doc and 'events' in existing_doc:
                # Find and update the event with matching id
                current_events = existing_doc.get('events', [])
                updated_events = []
                found = False
                
                for event in current_events:
                    if event.get('id') == event_data.get('id'):
                        # Update this event with new data
                        # If the event has a dateTime field, use it; otherwise use the old time field
                        processed_event_data = event_data.copy()
                        if 'dateTime' in event_data:
                            processed_event_data['time'] = event_data['dateTime']
                            del processed_event_data['dateTime']
                        updated_events.append(processed_event_data)
                        found = True
                    else:
                        updated_events.append(event)
                
                # If event was not found, return False
                if not found:
                    return False
                
                # Update the events array in the document
                result = self.settings_collection.update_one(
                    {"_id": existing_doc["_id"]},
                    {"$set": {"events": updated_events}}
                )
                return result.modified_count > 0
            else:
                return False
        except Exception as e:
            print(f"Error updating event: {e}")
            return False
    
    def delete_event(self, event_id: str) -> bool:
        """Delete an existing event from the database"""
        try:
            # Get the existing document
            existing_doc = self.settings_collection.find_one({})
            
            if existing_doc and 'events' in existing_doc:
                # Filter out the event with matching id
                current_events = existing_doc.get('events', [])
                updated_events = [event for event in current_events if event.get('id') != event_id]
                
                # Update the events array in the document
                result = self.settings_collection.update_one(
                    {"_id": existing_doc["_id"]},
                    {"$set": {"events": updated_events}}
                )
                return result.modified_count >= 0
            else:
                return False
        except Exception as e:
            print(f"Error deleting event: {e}")
            return False

    def get_face_recognition_models(self) -> list:
        """Retrieve all face recognition models from the database"""
        settings_doc = self.settings_collection.find_one({})
        if settings_doc and 'faceRecognitionModels' in settings_doc:
            return settings_doc['faceRecognitionModels']
        else:
            return []
    
    def save_face_recognition_model(self, model_data: Dict[str, Any]) -> bool:
        """Save a new face recognition model to the database"""
        try:
            # Get the existing document
            existing_doc = self.settings_collection.find_one({})
            
            if existing_doc:
                # Get current face recognition models and append the new one
                current_models = existing_doc.get('faceRecognitionModels', [])
                current_models.append(model_data)
                
                # Update the faceRecognitionModels array in the document
                result = self.settings_collection.update_one(
                    {"_id": existing_doc["_id"]},
                    {"$set": {"faceRecognitionModels": current_models}}
                )
                return result.modified_count >= 0  # Success if no error occurred
            
            else:
                # Create new settings document with the face recognition model
                self.settings_collection.insert_one({"faceRecognitionModels": [model_data]})
                return True
        except Exception as e:
            print(f"Error saving face recognition model: {e}")
            return False
    
    def delete_face_recognition_model(self, model_id: str) -> bool:
        """Delete a face recognition model from the database and filesystem"""
        try:
            # Get the existing document
            existing_doc = self.settings_collection.find_one({})
            
            if existing_doc and 'faceRecognitionModels' in existing_doc:
                # Find the model to delete (to get the file path)
                current_models = existing_doc.get('faceRecognitionModels', [])
                model_to_delete = None
                
                # Find the model with matching id
                for model in current_models:
                    if model.get('id') == model_id:
                        model_to_delete = model
                        break
                
                # Filter out the model with matching id
                updated_models = [model for model in current_models if model.get('id') != model_id]
                
                # Update the faceRecognitionModels array in the document
                result = self.settings_collection.update_one(
                    {"_id": existing_doc["_id"]},
                    {"$set": {"faceRecognitionModels": updated_models}}
                )
                
                # If database update was successful and we found the model, delete the image file
                if result.modified_count >= 0 and model_to_delete:
                    try:
                        # Delete the image file from filesystem
                        file_path = model_to_delete.get('filepath')
                        if file_path and os.path.exists(file_path):
                            os.remove(file_path)
                            print(f"Deleted face recognition image file: {file_path}")
                        else:
                            print(f"Image file not found or no filepath specified: {file_path}")
                    except Exception as file_error:
                        print(f"Warning: Could not delete image file {model_to_delete.get('filepath', 'unknown')}: {file_error}")
                        # Don't return False here - database deletion was successful
                
                return result.modified_count >= 0
            else:
                return False
        except Exception as e:
            print(f"Error deleting face recognition model: {e}")
            return False

# Create a global instance of SettingsManager
settings_manager = SettingsManager()
