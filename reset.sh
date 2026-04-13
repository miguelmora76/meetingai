docker build -f docker/Dockerfile -t localhost:5001/meetingai-app:latest . 
docker push localhost:5001/meetingai-app:latest
kubectl rollout restart deployment/meetingai-app -n meetingai 
kubectl rollout status deployment/meetingai-app -n meetingai
