<!-- To Build 
 docker build -t alishancoder/fastapi-project:1.0.2 .


  docker push alishancoder/fastapi-project:1.0.2  -->



docker buildx build --platform linux/amd64 -t alishancoder/fastapi-project:1.0.2 .
docker push alishancoder/fastapi-project:1.0.2
