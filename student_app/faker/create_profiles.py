import os
import pickle
import random
import sqlite3
from datetime import datetime
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier

root_dir = os.path.dirname(os.path.dirname(__file__),'..')
server_dir = os.path.join(root_dir, 'server')

# region Constants and Configuration
NUM_PROFILES = 10  # Number of profiles to create


PROFILE_DIR = os.path.dirname(os.path.dirname(__file__),'profiles')  # Path to save profiles
DB_PATH = os.path.join(server_dir, 'database.db')  # Path to the SQLite database
GRAPH_DIR = os.path.join(server_dir, 'graphs')  # Path to save graphs

# Define 70 personality-driven parameters
PERSONALITY_RANGES = {
    'age': (18, 45),
    'gender': ['male', 'female'],
    'academicInstitution': [
        'The Hebrew University of Jerusalem',
        'Tel Aviv University',
        'Ben-Gurion University',
        'Technion',
        'Bar-Ilan University',
        'Ariel University'
    ],
    'ecgKnowledge': [True, False],
    'persistenceLevel': (1, 10),
    'userSatisfaction': (1, 10),
    'learningRate': (1, 10),
    'motivation': (1, 10),
    'focusLevel': (1, 10),
    'stressResistance': (1, 10),
    'feedbackSensitivity': (1, 10),
    'riskTaking': (1, 10),
    'accuracyPreference': (1, 10),
    'adaptability': (1, 10),
    'consistency': (1, 10),
    'initialAnswerSpeed': (1, 10),
    'helpSeekingBehavior': (1, 10),
    'retention': (1, 10),
    'problemSolving': (1, 10),
    'logicalThinking': (1, 10),
    'emotionalState': (1, 10),
    'competitiveness': (1, 10),
    'cooperation': (1, 10),
    'selfReflection': (1, 10),
    'opennessToFeedback': (1, 10),
    'decisionMakingSpeed': (1, 10),
    'goalSetting': (1, 10),
    'timeManagement': (1, 10),
    'perfectionism': (1, 10),
    'adaptationToDifficulty': (1, 10),
    'multiTasking': (1, 10),
    'resourcefulness': (1, 10),
    'innovation': (1, 10),
    'memoryRecall': (1, 10),
    'strategicThinking': (1, 10),
    'curiosity': (1, 10),
    'energyLevel': (1, 10),
    'patience': (1, 10),
    'discipline': (1, 10),
    'reactionToFailure': (1, 10),
    'creativity': (1, 10),
    'confidence': (1, 10),
    'learningFromMistakes': (1, 10),
    'initiative': (1, 10),
    'empathy': (1, 10),
    'attentionToDetail': (1, 10),
    'independence': (1, 10),
    'procrastination': (1, 10),
    'resilience': (1, 10),
    'socialInteraction': (1, 10),
    'decisiveness': (1, 10),
    'persuasiveness': (1, 10),
    'teamwork': (1, 10),
    'leadership': (1, 10),
    'trustworthiness': (1, 10),
    'initiativeTaking': (1, 10),
    'flexibility': (1, 10),
    'problemOwnership': (1, 10),
    'emotionalIntelligence': (1, 10),
    'workEthic': (1, 10),
    'selfMotivation': (1, 10),
    'riskAssessment': (1, 10),
    'positiveAttitude': (1, 10),
    'dependability': (1, 10),
    'resourceManagement': (1, 10),
    'visionaryThinking': (1, 10),
    'delegation': (1, 10),
    'humor': (1, 10),
    'physicalEndurance': (1, 10),
    'mentalEndurance': (1, 10),
    'artisticExpression': (1, 10),
    'spatialAwareness': (1, 10),
    'kinestheticAwareness': (1, 10),
    'environmentalAwareness': (1, 10),
}

# endregion

# region Profile Management Functions

def generate_random_personality():
    """Generate a random personality profile based on the predefined ranges."""
    personality = {}
    for key, value in PERSONALITY_RANGES.items():
        if isinstance(value, tuple):
            personality[key] = random.randint(*value)
        elif isinstance(value, list):
            personality[key] = random.choice(value)
    return personality

def create_profile(profile_id, db_conn):
    """Create a new profile and save it to the database."""
    personality = generate_random_personality()
    profile = {
        'id': profile_id,
        'created_at': datetime.now().isoformat(),
        'params': personality,
        'model': RandomForestClassifier(),  # Untrained model
        'feedback_model': None,  # Placeholder for feedback model
    }
    insert_profile_into_db(profile, db_conn)
    save_profile(profile)

def insert_profile_into_db(profile, db_conn):
    """Insert the profile into the database."""
    cursor = db_conn.cursor()
    sql = """
    INSERT INTO users (id, age, gender, academicInstitution, ecgKnowledge)
    VALUES (?, ?, ?, ?, ?)
    """
    cursor.execute(sql, (
        profile['id'],
        profile['params']['age'],
        profile['params']['gender'],
        profile['params']['academicInstitution'],
        profile['params']['ecgKnowledge']
    ))
    db_conn.commit()

def save_profile(profile):
    """Save a profile to a file."""
    profile_path = os.path.join(PROFILE_DIR, f"profile_{profile['id']}.pkl")
    with open(profile_path, 'wb') as file:
        pickle.dump(profile, file)

# endregion

# region Main Execution
if __name__ == "__main__":
    db_conn = sqlite3.connect(DB_PATH)

    if not os.listdir(PROFILE_DIR):
        for profile_id in range(NUM_PROFILES):
            create_profile(profile_id, db_conn)
        print(f"{NUM_PROFILES} profiles created and inserted into the database successfully.")
    else:
        print("Profiles already exist, skipping creation.")

    db_conn.close()
# endregion
