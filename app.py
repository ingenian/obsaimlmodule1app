
# We are writing this code into a file called app.py using the line above.

# Import the streamlit library so we can make our web app screens easily
import streamlit as st

# --- STEP 1: Define a Helper Function to Check for Palindromes ---
def is_palindrome(text):
    # 1. We make all letters lowercase, so 'A' and 'a' look exactly the same to the computer!
    clean_text = text.lower()
    
    # 2. We remove anything that isn't a letter or a number (like spaces, commas, or question marks).
    # We only keep the characters if they are letters or numbers (alphanumeric).
    clean_text = "".join(character for character in clean_text if character.isalnum())
    
    # 3. If the user didn't type anything, we return False (it's not a palindrome)
    if len(clean_text) == 0:
        return False
        
    # 4. We reverse the text! In Python, [::-1] is a trick that flips a word backward.
    reversed_text = clean_text[::-1]
    
    # 5. We check if the clean text is exactly the same as the reversed text!
    # If they match, we say True (yes, it is!). Otherwise, we say False.
    return clean_text == reversed_text


# --- STEP 2: Designing the Beautiful Web Interface ---

# Put a friendly title at the very top of our app
st.title("🎈 My Super Fun Palindrome Checker")

# Write a small instruction manual for the user to read
st.write("Type any sentence below, and my smart computer brain will tell you if it reads the same backward and forward!")

# Create a text box where the user can type their magic sentence
user_input = st.text_input("Type your sentence here:", "")

# Create a button. When the user clicks it, we run our checker!
if st.button("Check My Sentence! 🚀"):
    if user_input:
        # Let's check the sentence using our helper function we made above!
        if is_palindrome(user_input):
            # If it returns True, we show a green success box!
            st.success("🎉 YES! That is a palindrome!")
            st.balloons() # Let's shoot some celebratory virtual balloons!
        else:
            # If it returns False, we show an orange warning box!
            st.warning("😢 No, that is not a palindrome. Try another one!")
    else:
        # If the user clicked the button but the text box is empty
        st.info("Please type a sentence first! ✍️")
