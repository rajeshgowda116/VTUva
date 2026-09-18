from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_documents(documents):

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )

    chunks = []

    for document in documents:

        texts = splitter.split_text(document["text"])

        for text in texts:

            chunks.append({
                "text": text,
                "page": document["page"],
                "source": document["source"]
            })

    return chunks