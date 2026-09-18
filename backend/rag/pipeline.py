from retriever import get_retriever
from generate import generate_answer


def ask_question(question):

    retriever = get_retriever()

    docs = retriever.invoke(question)

    print(f"\n🔎 Retrieved: {len(docs)}")

    for i, doc in enumerate(docs):

        print(f"\n--- Chunk {i + 1} ---")
        print("Source:", doc.metadata.get("source"))
        print("Page:", doc.metadata.get("page"))
        print(doc.page_content[:500])

    if not docs:
        return "No relevant information found."

    context = "\n\n".join(
        doc.page_content
        for doc in docs
    )

    return generate_answer(question, context)


if __name__ == "__main__":

    while True:

        question = input("\n❓ Ask a question: ")

        if question.lower() == "exit":
            break

        answer = ask_question(question)

        print("\n🤖 VTUva:")
        print(answer)