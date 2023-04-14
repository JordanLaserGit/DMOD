ARG REQUIRE="unzip wget gcc gcc-c++ glibc-devel gdal-devel libffi-devel openssl-devel rust cargo git proj proj-devel openblas lapack geos-devel python38 python38-pip"
################################################################################################################
################################################################################################################
##### Create foundational level build stage with initial structure
FROM rockylinux:8 as foundation
ARG REQUIRE

# Install required packages
RUN dnf -y upgrade
RUN dnf install -y epel-release
RUN dnf config-manager --set-enabled powertools
RUN dnf install -y ${REQUIRE} 
RUN dnf clean dbcache

# Along with setup and wheel to build, install all project pip3 dependencies for package building later
RUN mkdir /DIST && mkdir /dmod && pip3 install --upgrade pip
RUN for d in numpy pandas crypt scikit-learn; do for b in DIST; do mkdir -p /${b}/${d}; done; done

################################################################################################################
################################################################################################################
##### Create individual, semi-independent stages for building some of the longer-to-build packages to isolate
##### them in the cache.  This has the additional benefit of parallelizing these build steps.
FROM foundation as build_numpy_dep
RUN pip3 install --upgrade pip
ARG NUMPY_VERSION=">=1.18.0"
RUN pip wheel --cache-dir /CACHE --wheel-dir /DIST --prefer-binary numpy${NUMPY_VERSION}

############################################################
FROM foundation as build_cryptograph_dep
RUN pip3 install --upgrade pip
ARG CRYPTOGRAPHY_VERSION=""
RUN pip wheel --cache-dir /CACHE --wheel-dir /DIST --prefer-binary cryptography${CRYPTOGRAPHY_VERSION}

############################################################
FROM foundation as build_shapely_dep
RUN pip3 install --upgrade pip
ARG SHAPELY_VERSION=""
RUN pip wheel --cache-dir /CACHE --wheel-dir /DIST --prefer-binary shapely${SHAPELY_VERSION}

############################################################
# This one also requires numpy
FROM build_numpy_dep as build_pandas_dep
RUN pip3 install --upgrade pip
ARG PANDAS_VERSION=""
RUN pip wheel --cache-dir /CACHE --wheel-dir /DIST --prefer-binary pandas${PANDAS_VERSION}

############################################################
# This one requires numpy as well
FROM build_numpy_dep as build_sklearn_dep
RUN pip3 install --upgrade pip
ARG SKLEARN_VERSION=""
RUN pip wheel --cache-dir /CACHE --wheel-dir /DIST --prefer-binary scikit-learn${SKLEARN_VERSION}

################################################################################################################

################################################################################################################
################################################################################################################
##### Create base intermediate build stage that has all required dependencies for lib and service packages prepared
###### in its /DIST/ directory.
FROM foundation as basis
ARG REQUIRE

# Copy what we built so far in those other (hopefully cached) stages
COPY --from=build_pandas_dep /DIST/ /DIST/
COPY --from=build_pandas_dep /CACHE/ /CACHE/

COPY --from=build_cryptograph_dep /DIST/ /DIST/
COPY --from=build_cryptograph_dep /CACHE/ /CACHE/

COPY --from=build_shapely_dep /DIST/ /DIST/
COPY --from=build_shapely_dep /CACHE/ /CACHE/

COPY --from=build_sklearn_dep /DIST/ /DIST/
COPY --from=build_sklearn_dep /CACHE/ /CACHE/

RUN dnf -y upgrade
RUN dnf install -y epel-release
RUN dnf config-manager --set-enabled powertools
RUN dnf install -y ${REQUIRE} 
RUN dnf clean dbcache

RUN if [ ! -d /CACHE ]; then mkdir /CACHE; fi \
    && pip3 install --upgrade pip \
    && pip wheel --cache-dir /CACHE --wheel-dir /DIST --prefer-binary setuptools wheel geopandas

# Copy project requirements file, which should have everything needed to build any package within project
COPY ./requirements.txt /dmod/requirements.txt

# Along with setup and wheel to build, install any remaining (see above) project pip dependencies for package building later
RUN pip install wheel && pip wheel --cache-dir /CACHE --wheel-dir /DIST --prefer-binary -r /dmod/requirements.txt


################################################################################################################