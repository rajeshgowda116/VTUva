from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader


def load_pdfs(folder_path):

    folder = Path(folder_path)

    if not folder.exists():
        print("❌ Folder not found:", folder)
        return

    pdf_files = list(folder.rglob("*.pdf"))

    if not pdf_files:
        print("⚠️ No PDF files found")
        return

    total_pages = 0
    skipped_pages = 0

    for pdf_file in pdf_files:

        print(f"\n📄 Loading: {pdf_file}")

        try:
            loader = PyPDFLoader(str(pdf_file))

            for doc in loader.lazy_load():

                # Check blank page
                if not doc.page_content.strip():
                    skipped_pages += 1
                    print("⚠️ Blank page skipped")
                    continue

                total_pages += 1

                print(f"Page loaded: {total_pages}")
                print(doc.page_content[:200])
                print("-------------------")

        except Exception as e:
            print(f"❌ Error reading {pdf_file.name}: {e}")

    print("\n======================")
    print("Pages loaded:", total_pages)
    print("Blank pages skipped:", skipped_pages)
    print("======================")


if __name__ == "__main__":

    project_root = Path(__file__).resolve().parents[2]

    pdf_folder = project_root / "data" / "frist_sem"

    load_pdfs(pdf_folder)