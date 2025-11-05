#!/usr/bin/env python3
"""
Show hashed data from the database to demonstrate privacy protection
"""
from dotenv import load_dotenv
load_dotenv()

import sqlite3
from app.security import hash_for_logging

def show_hashed_data():
    """Show the hashed data stored in the database"""
    try:
        # Connect to the database
        conn = sqlite3.connect('healthcare_chatbot.db')
        cursor = conn.cursor()
        
        # Fetch recent chat logs
        cursor.execute("""
            SELECT id, hashed_query, hashed_response, timestamp 
            FROM chat_logs 
            ORDER BY timestamp DESC 
            LIMIT 10
        """)
        
        rows = cursor.fetchall()
        
        if rows:
            print("🔒 Hashed Chat Data in Database:")
            print("=" * 80)
            for row in rows:
                id, hashed_query, hashed_response, timestamp = row
                print(f"ID: {id}")
                print(f"Timestamp: {timestamp}")
                print(f"Hashed Query: {hashed_query[:50]}...")
                print(f"Hashed Response: {hashed_response[:50]}...")
                print("-" * 40)
        else:
            print("No chat logs found in database")
            
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

def demonstrate_hashing():
    """Show how original messages get hashed"""
    print("\n🔐 Hashing Demonstration:")
    print("=" * 50)
    
    sample_messages = [
        "Find hospitals in New York",
        "What is diabetes?",
        "I need a doctor"
    ]
    
    for message in sample_messages:
        hashed = hash_for_logging(message, use_hmac=True)
        print(f"Original: '{message}'")
        print(f"Hashed:   {hashed}")
        print()

if __name__ == "__main__":
    show_hashed_data()
    demonstrate_hashing()