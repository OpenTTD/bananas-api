FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpng-dev \
        libpython3-dev

COPY setup.py /code/
COPY src /code/src

RUN cd /code && python setup.py install && mkdir /result
RUN mv /code/build/*/*.so /result/

FROM python:3.11-slim

ARG BUILD_DATE=""
ARG BUILD_VERSION="dev"
ARG TARGETOS
ARG TARGETARCH

LABEL maintainer="OpenTTD Dev Team <info@openttd.org>"
LABEL org.opencontainers.image.created=${BUILD_DATE}
LABEL org.opencontainers.image.authors="OpenTTD Dev Team <info@openttd.org>"
LABEL org.opencontainers.image.url="https://github.com/OpenTTD/bananas-api"
LABEL org.opencontainers.image.source="https://github.com/OpenTTD/bananas-api"
LABEL org.opencontainers.image.version=${BUILD_VERSION}
LABEL org.opencontainers.image.licenses="GPLv2"
LABEL org.opencontainers.image.title="OpenTTD's content service API"
LABEL org.opencontainers.image.description="This is the HTTP API for OpenTTD's content service, called BaNaNaS."

# git is needed to clone BaNaNaS
# openssh-client is needed to git clone over ssh
# wget is temporary needed to download tusd.
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        libpng16-16 \
        openssh-client \
        wget \
    && rm -rf /var/lib/apt/lists/*

# We will be connecting to github.com, so populate their key already.
RUN mkdir -p ~/.ssh \
    && ssh-keyscan -t rsa github.com >> ~/.ssh/known_hosts

RUN wget -q https://github.com/tus/tusd/releases/download/v1.11.0/tusd_${TARGETOS}_${TARGETARCH}.tar.gz \
    && mkdir -p /tusd \
    && tar xf tusd_${TARGETOS}_${TARGETARCH}.tar.gz -C /tusd \
    && mv /tusd/tusd_${TARGETOS}_${TARGETARCH}/tusd /usr/bin/tusd \
    && rm -rf tusd_${TARGETOS}_${TARGETARCH}.tar.gz /tusd \
    && apt-get remove -y wget

WORKDIR /code

COPY requirements.txt \
        LICENSE \
        README.md \
        clients-development.yaml \
        clients-preview.yaml \
        clients-production.yaml \
        region-un-m49.csv \
        region-iso-3166-1.json \
        region-iso-3166-2.json \
        /code/
COPY licenses /code/licenses
# Needed for Sentry to know what version we are running
RUN echo "${BUILD_VERSION}" > /code/.version

RUN pip --no-cache-dir install -U pip \
    && pip --no-cache-dir install -r requirements.txt

# Validate that what was installed was what was expected
RUN pip freeze 2>/dev/null > requirements.installed \
        && diff -u --strip-trailing-cr requirements.txt requirements.installed 1>&2 \
        || ( echo "!! ERROR !! requirements.txt defined different packages or versions for installation" \
                && exit 1 ) 1>&2

COPY --from=builder /result/*.so /usr/local/lib/python3.11/site-packages/
COPY bananas_api /code/bananas_api

ENTRYPOINT ["python", "-m", "bananas_api"]
CMD ["--bind", "0.0.0.0", "--storage", "local", "--index", "local", "--user", "developer", "--client-file", "clients-development.yaml"]
