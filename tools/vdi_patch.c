//
// (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
// Licensed under the Apache v2.0 license.
//

#define	_GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <errno.h>
#include <unistd.h>
#include <string.h>
#include <sys/types.h>
#include <sys/stat.h>

#define	SENTINEL_STRING	"SFW - variables needed for patching system"
#define	PATCH_FORMAT "%sNODENAME=%s\nNODETYPE=%s\nHOSTNAME=%s\n"

void
usage(char *progname) {
	printf("usage : %s -d <base disk image> -v <VM image directory> -e <env file> -s <scenario> <VMlist>\n", progname);
	exit(1);
}

int
main(int argc, char *argv[]) {
	int		c;
	int 		fd;
	int		status;
	long int	i;
	long int	offset;
	long int	bytes;
	long int	file_index;
	long int	sentinel_length;
	unsigned char	*cp = NULL;
	unsigned char	*sp = NULL;
	unsigned char	*buffer = NULL;
	char		*env_file = NULL;
	char		*base_name = NULL;
	char		*vm_dir = NULL;
	char		src_vdi[256];
	char		dst_vdi[256];
	char		nodename[256];
	char		nodetype[256];
	char		hostname[256];
	char		scenario[256];
	char		environment[4096];
	char		patch_string[4096];
	struct stat	sbuf;

	//
	// Get the parameters
	//
	while (c = getopt(argc, argv, "e:b:v:"), c != EOF) {
		switch (c) {
		case 'b': base_name = optarg;   break;
		case 'v': vm_dir = optarg;      break;
		case 'e': env_file = optarg;    break;
		default:  usage(argv[0]);
		}
	}

	//
	// Read the environment file.
	//
	memset(environment, 0, sizeof(environment));

	if (fd = open(env_file, O_RDONLY), fd < 0) {
		printf("can't open %s (%d)\n", env_file, errno);
		return 0;
	} else if (read(fd, environment, sizeof(environment)) < 0) {
		printf("can't read %s (%d)\n", env_file, errno);
		return 0;
	} else if (close(fd) < 0) {
		printf("can't close %s (%d)\n", env_file, errno);
		return 0;
	}

	//
	// Get the scenario from the environment.
	//
	if (cp = strstr(environment, "SCENARIO="), cp == NULL) {
		printf("can't find scenario name in the environment file\n");
		return 0;
	}

	memset(scenario, 0, sizeof(scenario));
	sscanf(cp, "SCENARIO=%[^ \f\n\r\t\v]", scenario);

	//
	// Allocate our buffer.
	//
	sprintf(src_vdi, "%s/%s/%s.vdi", vm_dir, base_name, base_name);

	if (stat(src_vdi, &sbuf) < 0) {
		printf("can't stat %s (%d)\n", src_vdi, errno);
		return 0;
	}

	bytes = sbuf.st_size;
	if (buffer = calloc(1, bytes+128), buffer == NULL) {
		printf("can't malloc buffer (%d)\n", errno);
		return 0;
	}

	//
	// Open and read the src VDI file.
	//
	if (fd = open(src_vdi, O_RDONLY), fd < 0) {
		printf("can't open %s (%d)\n", src_vdi, errno);
		return 0;
	} else if (read(fd, buffer, bytes) != bytes) {
		printf("can't read %s (%d)\n", src_vdi, errno);
		return 0;
	} else if (close(fd) < 0) {
		printf("can't close %s (%d)\n", src_vdi, errno);
		return 0;
	}

	//
	// Find the sentinel string.
	//
	sentinel_length = strlen(SENTINEL_STRING);
	for (i = 0, sp = buffer; i < bytes; i++, sp++) {
		if (strncmp(sp, SENTINEL_STRING, sentinel_length) == 0) {
			break;
		}
	}

	if (sp = strchr(sp, '\n'), sp == NULL) {
		printf("invalid VDI format\n");
		return 0;
	}

	sp++;

	//
	// Write out the dst VDI file.
	//
	for (i = optind; i < argc; i++) {
		sscanf(argv[i], "%[^,],%[^,],%[^,]", nodename, nodetype, hostname);

		memset(patch_string, '\0', sizeof(patch_string));
		sprintf(patch_string, PATCH_FORMAT, environment, nodename, nodetype, hostname);
		memcpy(sp, patch_string, strlen(patch_string));

		sprintf(dst_vdi, "%s/%s_%s/%s_%s.vdi", vm_dir, scenario, nodename, scenario, nodename);
		printf("writing %s_%s variables\n", scenario, nodename);

		if (fd = open(dst_vdi, O_RDWR, 0644), fd < 0) {
			printf("can't open %s (%d)\n", dst_vdi, errno);
			return 0;
		} else if (write(fd, buffer, bytes) < 0) {
			printf("can't write %s (%d)\n", dst_vdi, errno);
			return 0;
		} else if (close(fd) < 0) {
			printf("can't close %s (%d)\n", dst_vdi, errno);
			return 0;
		}

		memset(sp, ' ', strlen(patch_string));
	}

	return 0;
}
