to create a clone of google drive but to be simple and clean
simpledrive is basically a clone of the google drive which stores the data.
Mongobd stroes the data of the file or image which we upload not the actual file.
Minio stores the actual data.
python backend is the set of instructions how our simple drive needs to works. it is like heart of our simpledrive whch is making our simpledrive work.
Nginx is browser which handles the request from the fetch().
 docker compose up -d --build
 Frontend: http://localhost:8080
 Backend testing page: http://localhost:8000/docs
  MinIO file console: http://localhost:9001
  
                 USER
                  ↓
          Selects a file
                  ↓
             FRONTEND
          (Browser JavaScript)
                  ↓
             FormData
                  ↓
              fetch()
                  ↓
                Nginx
                  ↓
          Backend / FastAPI
             ↙          ↘
            ↓            ↓
        MongoDB         MinIO
      file metadata    actual file