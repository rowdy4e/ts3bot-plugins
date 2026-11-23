FROM alpine:3.20
RUN apk add --no-cache curl jq
COPY run.sh /run.sh
ENTRYPOINT ["/bin/sh", "/run.sh"]
