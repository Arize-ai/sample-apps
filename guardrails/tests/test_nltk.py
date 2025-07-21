#!/usr/bin/env python3
"""
Test script to verify NLTK tokenization works correctly
"""

import nltk

def test_nltk_tokenization():
    """Test that NLTK sentence tokenization works"""
    try:
        # Test sentence tokenization
        test_text = "Hello world! This is a test sentence. How are you today?"
        sentences = nltk.sent_tokenize(test_text)
        
        print("NLTK Tokenization Test:")
        print(f"Input text: {test_text}")
        print(f"Tokenized sentences: {sentences}")
        print(f"Number of sentences found: {len(sentences)}")
        
        if len(sentences) == 3:
            print("✓ NLTK tokenization working correctly!")
            return True
        else:
            print("✗ NLTK tokenization may not be working as expected")
            return False
            
    except Exception as e:
        print(f"✗ NLTK tokenization failed: {e}")
        return False

if __name__ == "__main__":
    success = test_nltk_tokenization()
    if success:
        print("\nYour GuardRails GibberishText validator should now work correctly!")
    else:
        print("\nThere may still be issues with NLTK. Please check the setup.") 