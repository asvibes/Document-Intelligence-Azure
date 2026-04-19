\# 📄 Document Intelligence API (Azure)



A FastAPI-based backend service that analyzes documents using Azure Document Intelligence and returns structured data.



\---



\## 🚀 Features



\* 📑 Analyze documents (PDFs, images, etc.)

\* ⚡ FastAPI backend for high performance

\* 🌐 Interactive API docs with Swagger UI

\* ☁️ Integration with Azure AI Document Intelligence



\---



\## 🛠️ Tech Stack



\* Python 🐍

\* FastAPI ⚡

\* Uvicorn 🌐

\* Azure Document Intelligence ☁️



\---



\## 📂 Project Structure



```

Document-Intelligence-Azure/

│── document\_intelligence.py   # Main FastAPI app

│── index.html                 # Frontend (if used)

│── \_\_pycache\_\_/               # Ignored files

│── .gitignore

│── README.md

```



\---



\## ⚙️ Setup Instructions



\### 1. Clone the repository



```

git clone https://github.com/asvibes/Document-Intelligence-Azure.git

cd Document-Intelligence-Azure

```



\---



\### 2. Create virtual environment



```

python -m venv .venv

.venv\\Scripts\\activate

```



\---



\### 3. Install dependencies



```

pip install -r requirements.txt

```



\---



\### 4. Run the server



```

uvicorn document\_intelligence:app --reload

```



\---



\## 🌐 API Endpoints



| Method | Endpoint   | Description               |

| ------ | ---------- | ------------------------- |

| GET    | `/docs`    | Swagger UI                |

| POST   | `/analyze` | Analyze uploaded document |



\---



\## 📸 API Preview



Once running, open:



👉 http://127.0.0.1:8000/docs



\---



\## ⚠️ Notes



\* Make sure Azure credentials are properly configured

\* Do not upload sensitive keys to GitHub



\---



\## 💡 Future Improvements



\* Add authentication 🔐

\* Improve UI 🎨

\* Deploy to cloud ☁️



\---



\## 🤝 Contributing



Feel free to fork and improve the project!



\---



\## 📜 License



This project is open-source and available under the MIT License.



\---



\## ❤️ Author



Made with dedication by \*\*asvibes\*\*



