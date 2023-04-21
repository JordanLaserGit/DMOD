PROJECT_PARENT="$(cd "$(dirname "${0}")"; pwd)"
DMOD_DIR=''
EMAIL=''
INFO='Rapidly install DMOD on AWS cloud instance'

usage()
{
    local _O="${NAME:?}:
${INFO:?}

Usage:
    ${NAME:?} -h|-help|--help
    ${NAME:?} [opts]

Options:
    --project_parent <dir>
        Set the directory in which DMOD will be cloned to.
        By default, the parent directory of this script will be used.
        - ${PROJECT_PARENT:-?}/

    --email <name>
        email address that will be used in creating ssl keys
"
    echo "${_O}" 2>&1
}

while [ ${#} -gt 0 ]; do
    case "${1}" in
		--project_parent)
			PROJECT_PARENT="${2}"
			DMOD_DIR="${PROJECT_PARENT}/DMOD"
			shift
			;;
		--email)
			EMAIL="${2}"
			shift
			;;			
        -h|--help|-help)
            usage
            exit
            ;;

        *)
    esac
    shift
done

# cd into the target directory
cd "${PROJECT_PARENT}"

# Clone DMOD repo
if [ ! -d "${DMOD_DIR}" ]; then
	git clone https://github.com/NOAA-OWP/DMOD.git
else
	echo "DMOD directory already exists, skipping git clone"
fi

# Make ssl directories and generate ssl certs
if [ -d "${DMOD_DIR}/ssl" ]; then
	echo "ssl directory exists, assuming certs do not need to be recreated"
else
	mkdir ${DMOD_DIR}/ssl

	mkdir "${DMOD_DIR}/ssl/dataservice"
	mkdir "${DMOD_DIR}/ssl/local"
	mkdir "${DMOD_DIR}/ssl/partitionerservice"
	mkdir "${DMOD_DIR}/ssl/requestservice"
	mkdir "${DMOD_DIR}/ssl/scheduler"

	# Generate keys
	# gen_cert has more options than this!
	"${DMOD_DIR}/scripts/gen_cert.sh" -d "${DMOD_DIR}/ssl/dataservice" -email "${EMAIL}"
	"${DMOD_DIR}/scripts/gen_cert.sh" -d "${DMOD_DIR}/ssl/local" -email "${EMAIL}"
	"${DMOD_DIR}/scripts/gen_cert.sh" -d "${DMOD_DIR}/ssl/partitionerservice" -email "${EMAIL}"
	"${DMOD_DIR}/scripts/gen_cert.sh" -d "${DMOD_DIR}/ssl/requestservice" -email "${EMAIL}"
	"${DMOD_DIR}/scripts/gen_cert.sh" -d "${DMOD_DIR}/ssl/scheduler" -email "${EMAIL}"
fi

# Make DMOD the current working directory
cd "${DMOD_DIR}"

# Create python virtual environment
if [ -d "${DMOD_DIR}/venv" ]; then
	echo "Python virtual environment already exists"
else
	# Create and activate virtual environment
	python -m venv "${DMOD_DIR}/venv"
fi

source "${DMOD_DIR}/venv/bin/activate"

# Copy example.env to AWS.env
cp example.env AWS_example.env

# install docker compose
sudo dnf install docker-compose

# Add users to docker group
sudo groupadd docker
sudo usermod -aG docker ${USER}

# Update python and deps
# Again, lots of options here i'm ignoring
./scripts/update_package.sh

# update packages
if ./scripts/control_stack.sh py-sources build --env-file "${DMOD_DIR}/AWS_example.env"; then
	echo "Done with py-sources build"
else
	echo "py-sources build failed!!"
	exit
fi     

# May need to implement ssh keys here before main build
        
if ./scripts/control_stack.sh main build --env-file "${DMOD_DIR}/AWS_example.env"; then
        echo "Done with main build"
else
        echo "main build failed!!"
		exit
fi

