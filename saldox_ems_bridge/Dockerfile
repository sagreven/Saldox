ARG BUILD_FROM
FROM ${BUILD_FROM}

ENV LANG=C.UTF-8 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apk add --no-cache python3 py3-pip

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --break-system-packages -r /app/requirements.txt

COPY saldox_addon /app/saldox_addon
COPY run.sh /run.sh
RUN chmod +x /run.sh

CMD ["/run.sh"]
# cache-bust: 1783835330
# rebuild trigger Tue, Jul 14, 2026  1:44:04 PM
