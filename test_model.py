import pickle

# Load model and vectorizer
model = pickle.load(open("emotion_model.pkl", "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))

# Test input
while True:
    user_input = input("Enter a sentence (type 'exit' to stop): ")

    if user_input.lower() == "exit":
        break

    input_vec = vectorizer.transform([user_input])
    prediction = model.predict(input_vec)

    print("Predicted Emotion:", prediction[0])