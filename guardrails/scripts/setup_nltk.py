#!/usr/bin/env python3
"""
Setup script to download required NLTK data for GuardRails GibberishText validator
"""

import nltk
import os
import ssl
import urllib.request
from pathlib import Path

def fix_ssl_context():
    """Fix SSL context for macOS certificate issues"""
    try:
        # Try to create an unverified SSL context as a fallback
        import ssl
        ssl._create_default_https_context = ssl._create_unverified_context
        print("SSL context updated to handle certificate issues")
    except Exception as e:
        print(f"Could not update SSL context: {e}")

def download_nltk_data():
    """Download required NLTK data for sentence tokenization"""
    
    # First, try to fix SSL issues
    fix_ssl_context()
    
    try:
        print("Downloading NLTK punkt_tab data...")
        result = nltk.download('punkt_tab', quiet=False)
        if result:
            print("NLTK punkt_tab data downloaded successfully!")
        else:
            print("Failed to download punkt_tab data")
            
        # Also download punkt (legacy) as a fallback
        print("Downloading NLTK punkt data as fallback...")
        result = nltk.download('punkt', quiet=False)
        if result:
            print("NLTK punkt data downloaded successfully!")
        else:
            print("Failed to download punkt data")
            
    except Exception as e:
        print(f"Error downloading NLTK data: {e}")
        print("\nTrying manual installation...")
        
        # Provide manual installation instructions
        print("\n" + "="*50)
        print("MANUAL INSTALLATION INSTRUCTIONS:")
        print("="*50)
        print("If automatic download fails, you can manually install the data:")
        print("1. Run the following commands in Python:")
        print("   import nltk")
        print("   import ssl")
        print("   ssl._create_default_https_context = ssl._create_unverified_context")
        print("   nltk.download('punkt_tab')")
        print("   nltk.download('punkt')")
        print("\n2. Or install certificates using:")
        print("   /Applications/Python\\ 3.x/Install\\ Certificates.command")
        print("   (Replace 3.x with your Python version)")
        print("="*50)
        
        return False
    
    return True

def verify_nltk_data():
    """Verify that the required NLTK data is available"""
    try:
        # Try to find the data
        nltk.data.find('tokenizers/punkt_tab')
        print("✓ punkt_tab data found")
        return True
    except LookupError:
        try:
            nltk.data.find('tokenizers/punkt')
            print("✓ punkt data found (legacy)")
            return True
        except LookupError:
            print("✗ No NLTK tokenizer data found")
            return False

if __name__ == "__main__":
    print("Setting up NLTK data for GuardRails GibberishText validator...")
    
    # Check if data is already available
    if verify_nltk_data():
        print("\nNLTK data is already available! No setup needed.")
    else:
        success = download_nltk_data()
        if success:
            if verify_nltk_data():
                print("\nNLTK setup complete! You can now run your GuardRails application.")
            else:
                print("\nNLTK setup completed but data verification failed.")
                print("Please try the manual installation steps above.")
        else:
            print("\nNLTK setup failed. Please try the manual installation steps above.") 