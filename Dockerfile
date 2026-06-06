FROM alpine:3.20
RUN apk add --no-cache bash curl ca-certificates
WORKDIR /app
COPY field-monitor.json create-agent.sh ./
RUN chmod +x create-agent.sh
ENTRYPOINT ["./create-agent.sh"]
