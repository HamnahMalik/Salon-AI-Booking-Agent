from rag import ask_salon

questions = [
    "How much is a facial?",
    "Are you open on Sunday?",
    "Who does hair coloring?",
    "Do you offer home service?"
]

for question in questions:
    print("\nQUESTION:", question)
    print("ANSWER:", ask_salon(question))
