FROM python:3.8-slim

ARG BUILD_DATE=""
ARG BUILD_VERSION="dev"

LABEL maintainer="truebrain@openttd.org"
LABEL org.label-schema.schema-version="1.0"
LABEL org.label-schema.build-date=${BUILD_DATE}
LABEL org.label-schema.version=${BUILD_VERSION}

# git is a dependency of the code.
# wget is temporary needed to download tusd.
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        openssh-client \
        wget \
    && rm -rf /var/lib/apt/lists/*

# We will be connecting to github.com, so populate their key already.
RUN mkdir -p ~/.ssh \
    && ssh-keyscan -t rsa github.com >> ~/.ssh/known_hosts

RUN wget -q https://github.com/tus/tusd/releases/download/v1.1.0/tusd_linux_amd64.tar.gz \
    && mkdir -p /tusd \
    && tar xf tusd_linux_amd64.tar.gz -C /tusd \
    && mv /tusd/tusd_linux_amd64/tusd /usr/bin/tusd \
    && rm -rf tusd_linux_amd64.tar.gz /tusd \
    && apt-get remove -y wget

WORKDIR /code

COPY requirements.txt \
        LICENSE \
        README.md \
        .version \
        /code/
COPY licenses /code/licenses
# Needed for Sentry to know what version we are running
RUN echo "${BUILD_VERSION}" > /code/.version

RUN pip --no-cache-dir install -r requirements.txt

# Validate that what was installed was what was expected
RUN pip freeze 2>/dev/null > requirements.installed \
    && diff -u --strip-trailing-cr requirements.txt requirements.installed 1>&2 \
    || ( echo "!! ERROR !! requirements.txt defined different packages or versions for installation" \
        && exit 1 ) 1>&2

COPY bananas_api /code/bananas_api

ENTRYPOINT ["python", "-m", "bananas_api"]
CMD ["--bind", "0.0.0.0", "--storage", "local", "--index", "local", "--user", "developer"]
