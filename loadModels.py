import os
import pickle
def load_models():
    try:
        working_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Load heart disease model
        heart_model_path = os.path.join(working_dir, 'saved_models', 'heart_disease_model.pkl')
        if os.path.exists(heart_model_path):
            heart_model = pickle.load(open(heart_model_path, 'rb'))
            print("Heart model loaded successfully")
        else:
            heart_model = None
            print("Heart model not found")
        
        # Load diabetes model
        diabetes_model_path = os.path.join(working_dir, 'saved_models', 'diabetes_model.pkl')
        if os.path.exists(diabetes_model_path):
            diabetes_model = pickle.load(open(diabetes_model_path, 'rb'))
            print("Diabetes model loaded successfully")

        else:
            diabetes_model = None
            print("Diabetes model not found")
            
        # Load Parkinson's model
        parkinsons_model_path = os.path.join(working_dir, 'saved_models', 'parkinsons_model.pkl')
        if os.path.exists(parkinsons_model_path):
            parkinsons_model = pickle.load(open(parkinsons_model_path, 'rb'))
            print("Parkinsons model loaded successfully")
        else:
            print("Parkinsons model not found")
            parkinsons_model = None
        
        return {
            'heart': heart_model,
            'diabetes': diabetes_model,
            'parkinsons': parkinsons_model
        }
    except Exception as e:
        print(f"Error loading models: {str(e)}")
        return {
            'heart': None,
            'diabetes': None,
            'parkinsons': None
        }
    
#Model Loading
#testing git