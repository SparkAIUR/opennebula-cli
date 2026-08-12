"""Official command descriptions extracted from OpenNebula 7.0.2 help output."""

# ruff: noqa: E501

from __future__ import annotations

OFFICIAL_COMMAND_DESCRIPTIONS: dict[str, dict[str, str]] = {
    "acl": {
        "create": "Adds a new ACL rule",
        "delete": "Deletes an existing ACL rule",
        "list": "Lists the ACL rule set.",
    },
    "backupjob": {
        "backup": "Start the Backup Job execution.",
        "cancel": "Cancel pending Backup Job, remove Virtual Machines from the outdated "
        "list, call cancel action on all ongoing VM backup operations.",
        "chgrp": "Changes the Backup Job group",
        "chmod": "Changes the BackupJob permissions",
        "chown": "Changes the Backup Job owner and group",
        "create": "Creates a new Backup Job onebackupjob create weekly_backup.tmpl cat "
        "$bj_template | onebackupjob create",
        "delete": "Deletes the given Backup Job",
        "list": "Lists Backup Jobs in the pool.",
        "lock": "Locks a Backup Job to prevent certain actions defined by different levels.",
        "priority": "Change the priority of the Backup Job.",
        "rename": "Renames the Backup Job",
        "retry": "Retry failed Backup Job.",
        "sched-delete": "Remove a Scheduled Action from the Backup Job.",
        "sched-update": "Update a Scheduled Action for the Backup Job.",
        "show": "Shows information for the given Backup Job",
        "unlock": "Unlocks an Backup Job.",
        "update": "Update the Backup Job contents.",
    },
    "cfg": {
        "diff": "Detect changes in configuration files",
        "generate": "INTERNAL: Generates automatic migration descriptor between 2 versions",
        "init": "Initialize OneCfg configuration version based on OpenNebula version",
        "patch": "Apply changes to configuration files",
        "status": "Show information about current installation",
        "upgrade": "Upgrade configuration files",
        "validate": "Read all base configuration files and check validity",
    },
    "cluster": {
        "adddatastore": "Adds a Datastore to the given Cluster",
        "addhost": "Adds a Host to the given Cluster",
        "addvnet": "Adds a Virtual Network to the given Cluster",
        "create": "Creates a new Cluster",
        "deldatastore": "Deletes a Datastore from the given Cluster",
        "delete": "Deletes the given Cluster",
        "delhost": "Deletes a Host from the given Cluster",
        "delvnet": "Deletes a Virtual Network from the given Cluster",
        "list": "Lists Clusters in the pool.",
        "optimize": "Create optimization plan for Cluster",
        "plandelete": "Delete the optimization plan",
        "planexecute": "Start applying the optimization plan",
        "rename": "Renames the Cluster",
        "show": "Shows information for the given Cluster",
        "update": "Update the template contents.",
    },
    "datastore": {
        "chgrp": "Changes the Datastore group",
        "chmod": "Changes the Datastore permissions",
        "chown": "Changes the Datastore owner and group",
        "create": "Creates a new Datastore from the given template A template can be passed "
        "as a file with or the content via STDIN Bash symbols must be escaped on "
        "STDIN passing",
        "delete": "Deletes the given Datastore",
        "disable": "Disables the given Datastore.",
        "enable": "Enables the given Datastore.",
        "list": "Lists Datastores in the pool.",
        "rename": "Renames the Datastore",
        "show": "Shows information for the given Datastore",
        "update": "Update the template contents.",
    },
    "db": {
        "--expr": "examples: UNAME=oneadmin, TEMPLATE/NIC/NIC_ID>0 If you want to change a value "
        "use a third parameter.",
        "--id": "For example to update the XML document of VM 23: onedb update-body vm --id 23 "
        "**WARNING**: This action is done while OpenNebula is running.",
        "--seq": "For example to update the 3rd record of VM 0 onedb update-history --id 0 --seq 3 "
        "**WARNING**: This action is done while OpenNebula is running.",
        "backup": "Dumps the DB to a file specified in the argument",
        "change-body": "Changes a value from the body of an object.",
        "change-history": "Changes a value from a history record of a VM.",
        "fsck": "Checks the consistency of the DB, and fixes the problems found",
        "history": "Prints the upgrades history",
        "patch": "Applies a database patch file",
        "purge-done": "Deletes all VMs in DONE state **WARNING**: This action is done while "
        "OpenNebula is running.",
        "purge-history": "Deletes all but the last two history records from non DONE VMs.",
        "restore": "Restores the DB from a backup file.",
        "show-body": "Show body of an object.",
        "show-history": "Show body of a history record.",
        "sqlite2mysql": "Migrates a SQLite OpenNebula Database to MySQL",
        "update-body": "Update body of an object.",
        "update-history": "Update history record of a VM.",
        "upgrade": "Upgrades the DB to the latest version where <version> : DB version (e.g.",
        "version": "Prints the current DB version.",
    },
    "flow": {
        "action": "Perform an action on all the Virtual Machines of a given role.",
        "add-role": "Add new role to running service",
        "chgrp": "Changes the service group",
        "chmod": "Changes the service permissions",
        "chown": "Changes the service owner and group",
        "delete": "Delete a given service To force service removal please use 'oneflow recover "
        "--delete <service_id>' command",
        "list": "List the available services",
        "purge-done": "Purge and delete services in DONE state",
        "recover": "Recover a failed service, cleaning the failed VMs.",
        "release": "Release roles of a service on hold",
        "remove-role": "Remove role from running service",
        "rename": "Renames the Service",
        "scale": "Scale a role to the given cardinality",
        "service": "Perform an action on all the Virtual Machines of a given service.",
        "show": "Show detailed information of a given service",
        "top": "Top the available services",
        "update": "Update the template contents.",
    },
    "flow-template": {
        "chgrp": "Changes the service template group",
        "chmod": "Changes the service template permissions",
        "chown": "Changes the service template owner and group",
        "clone": "Creates a new Service Template from an existing one",
        "create": "Create a new Service Template from a json service definition A "
        "template can be passed as a file with or the content via STDIN Bash "
        "symbols must be escaped on STDIN passing",
        "delete": "Delete a given Service Template",
        "instantiate": "Instantiate a Service Template Optionally append modifications "
        "with a json service definition A template can be passed as a "
        "file with or the content via STDIN Bash symbols must be escaped "
        "on STDIN passing",
        "list": "List the available Service Templates",
        "rename": "Renames the Service Template",
        "show": "Show detailed information of a given Service Template",
        "top": "List the available Service Templates continuously",
        "update": "Update the template contents.",
    },
    "group": {
        "addadmin": "Adds a User to the Group administrators set",
        "batchquota": "Sets the quota limits in batch for various groups.",
        "create": "Creates a new Group.",
        "defaultquota": "Sets the default quota limits for the groups.",
        "deladmin": "Removes a User from the Group administrators set",
        "delete": "Deletes the given Group",
        "list": "Lists Groups in the pool.",
        "quota": "Set the quota limits for the group.",
        "show": "Shows information for the given Group",
        "update": "Update the template contents.",
    },
    "hook": {
        "create": "Creates a new Hook from the given description - using a Hook description "
        "file: onehook create hook.tmpl - using a Hook description file via stdin: cat "
        "$hook_template | onehook create",
        "delete": "Deletes the given Hook",
        "list": "Lists Hooks in the pool.",
        "lock": "Locks a Hook to prevent certain actions defined by different levels.",
        "log": "Get logs about hook executions ~ $ onehook log --since 09/19/19 # returns all "
        "logs since that date ~ $ onehook log --error # returns all failing execs logs ~ "
        "$ onehook log --hook-id 0 # returns all logs from hook 0",
        "rename": "Renames the Hook",
        "retry": "Retry a previous hook execution.",
        "show": "Shows information for the given Hook.",
        "top": "Lists Hooks continuously",
        "unlock": "Unlocks a Hook for unlock any actions with this Hook.",
        "update": "Update the Hook contents.",
    },
    "host": {
        "create": "Creates a new Host",
        "delete": "Deletes the given Host",
        "disable": "Disables the given host: - monitor: enabled - scheduler deployment: disabled "
        "- manual deployment: enabled",
        "enable": "Enables the given host, fully operational",
        "flush": "Disables the host and reschedules all the running VMs in it.",
        "forceupdate": "Forces host monitoring update onehost forceupdate host01 onehost "
        "forceupdate host01,host02,host03 onehost forceupdate -c myCluster",
        "list": "Lists Hosts in the pool.",
        "monitoring": "Show monitoring metrics in a graphic",
        "offline": "Sets the host offline: - monitor: disabled - scheduler deployment: disabled "
        "- manual deployment: disabled",
        "rename": "Renames the Host",
        "show": "Shows information for the given Host",
        "sync": "Synchronizes probes in /var/lib/one/remotes ($ONE_LOCATION/var/remotes in "
        "self-contained installations) with Hosts.",
        "top": "Lists Hosts continuously",
        "update": "Update the template contents.",
    },
    "image": {
        "chgrp": "Changes the Image group",
        "chmod": "Changes the Image permissions",
        "chown": "Changes the Image owner and group",
        "chtype": "Changes the Image's type",
        "clone": "Creates a new Image from an existing one",
        "create": "Creates a new Image oneimage create -d default centOS.tmpl A template can be "
        "passed as a file with or the content via STDIN Bash symbols must be escaped "
        'on STDIN passing - new image "arch" using a path: oneimage create -d default '
        "--name arch --path /tmp/arch.img - new persistent image, OS type and qcow2 "
        "format: oneimage create -d 1 --name ubuntu --path /tmp/ubuntu.qcow2 \\ "
        '--prefix sd --type OS --format qcow2 \\ --description "A OS plain '
        'installation" \\ --persistent - a datablock image of 400MB: oneimage create '
        "-d 1 --name data --type DATABLOCK --size 400",
        "delete": "Deletes the given Image",
        "disable": "Disables the given Image",
        "enable": "Enables the given Image",
        "list": "Lists Images in the pool.",
        "lock": "Locks an Image to prevent certain actions defined by different levels.",
        "nonpersistent": "Makes the given Image non persistent.",
        "orphans": "Shows orphans images (i.e images not referenced in any template).",
        "persistent": "Makes the given Image persistent.",
        "rename": "Renames the Image",
        "restore": "Restore a backup image.",
        "show": "Shows information for the given Image",
        "snapshot-delete": "Deletes a snapshot from the image",
        "snapshot-flatten": "Flattens the snapshot and removes all other snapshots in the image",
        "snapshot-revert": "Reverts image state to a snapshot",
        "top": "Lists Images continuously",
        "unlock": "Unlocks an Image.",
        "update": "Update the template contents.",
    },
    "log": {
        "get": "Gets log from an specific OpenNebula service",
        "get-service": "Gets Service log",
        "get-vm": "Gets VM log",
    },
    "market": {
        "chgrp": "Changes the Marketplace group",
        "chmod": "Changes the Marketplace permissions",
        "chown": "Changes the Marketplace owner and group",
        "create": "Creates a new Marketplace from the given template A template can be passed "
        "as a file with or the content via STDIN Bash symbols must be escaped on "
        "STDIN passing",
        "delete": "Deletes the given Marketplace",
        "disable": "Disables the marketplace.",
        "enable": "Enables the marketplace",
        "list": "Lists Marketplaces.",
        "rename": "Renames the Marketplace",
        "show": "Shows Marketplace information",
        "update": "Update the template contents.",
    },
    "marketapp": {
        "chgrp": "Changes the marketplace app group",
        "chmod": "Changes the marketplace app permissions",
        "chown": "Changes the marketplace app owner and group",
        "create": "Creates a new marketplace app in the given marketplace A template can be "
        "passed as a file with or the content via STDIN Bash symbols must be "
        "escaped on STDIN passing",
        "delete": "Deletes the given marketplace app",
        "disable": "Disables the marketplace app.",
        "enable": "Enables the marketplace app",
        "export": "Exports the marketplace app to the OpenNebula cloud",
        "list": "Lists marketplace apps.",
        "lock": "Locks a marketplace app to prevent certain actions defined by different levels.",
        "rename": "Renames the marketplace app",
        "service-template": "Imports a service template into the marketplace",
        "show": "Shows information for the given marketplace app",
        "unlock": "Unlocks a marketplace app.",
        "update": "Update the template contents for the app.",
        "vm": "Imports a VM into the marketplace",
        "vm-template": "Imports a VM template into the marketplace",
    },
    "secgroup": {
        "chgrp": "Changes the Security Group's group",
        "chmod": "Changes the Security Group permissions",
        "chown": "Changes the Security Group's owner and group",
        "clone": "Creates a new Security Group from an existing one",
        "commit": "Commit SG changes to associated VMs.",
        "create": "Creates a new Security Group from the given description",
        "delete": "Deletes the given Security Group",
        "list": "Lists Security Group in the pool.",
        "rename": "Renames the Security Group",
        "show": "Shows information for the given Security Group",
        "update": "Update the template contents.",
    },
    "showback": {
        "calculate": "Calculates the showback records",
        "list": "Returns the showback records",
    },
    "swap": {
        "convert": "Convert a vCenter Virtual Machine VOPTS='--vcenter 12.34.56.78 --vuser "
        "Administrator@vsphere.local --vpass changeme123' - Convert a virtual "
        "machine: oneswap convert vm-1234 $VOPTS [--fallback|--custom] [--network ID] "
        "[--datacenter ID] - Convert a virtual machine from ESXi directly: oneswap "
        "convert vm-1234 $VOPTS --esxi 12.34.56.79 --esxi_pass changeme123 "
        "[--esxi_user root] - Convert a vCenter virtual machine utilizing the "
        "proprietary VDDK library(faster transfer usually): oneswap convert vm-1234 "
        "$VOPTS --vddk /path/to/vddk-lib - Convert using OpenNebula Custom Conversion "
        "(useful for distributions which are not supported or fail to convert) You "
        "can also define --fallback instead of --custom, which will first attempt "
        "virt-v2v style, then fallback to custom.",
        "import": "Import an OVA as VM or VMDK as Image file exported from VMware - import VM "
        "from an OVA file: oneswap import --ova OVA.ova - import VM from an OVF file: "
        "oneswap import --ova /path/to/files - import Image from an VMDK file: oneswap "
        "import --vmdk disk.vmdk",
        "list": "Show a list with vCenter objects, default to VM - listing all VMs: oneswap list "
        "vms - listing available Clusters: oneswap list clusters - listing available vms "
        "in a Datacenter and Cluster: oneswap list vms --datacenter DCName --cluster "
        "Cluster2",
    },
    "template": {
        "chgrp": "Changes the Template group",
        "chmod": "Changes the Template permissions",
        "chown": "Changes the Template owner and group",
        "clone": "Creates a new Template from an existing one",
        "create": "Creates a new VM Template from the given description - using a VM "
        "Template description file: onetemplate create vm_description.tmpl A "
        "template can be passed as a file with or the content via STDIN Bash "
        'symbols must be escaped on STDIN passing - new VM Template named "arch '
        'vm" with a disk and a nic: onetemplate create --name "arch vm" --memory '
        "128 --cpu 1 \\ --disk arch --network private_lan - using two disks: "
        'onetemplate create --name "test vm" --memory 128 --cpu 1 \\ --disk '
        "arch,data",
        "delete": "Deletes the given Template",
        "instantiate": "Creates a new VM instance from the given Template.",
        "list": "Lists Templates in the pool.",
        "lock": "Locks a Template to prevent certain actions defined by different levels.",
        "rename": "Renames the Template",
        "show": "Shows information for the given Template",
        "top": "Lists Templates continuously",
        "unlock": "Unlocks a Template.",
        "update": "Update the template contents.",
    },
    "user": {
        "addgroup": "Adds the User to a secondary group",
        "batchquota": "Sets the quota limits in batch for various users.",
        "chauth": "Changes the User's auth driver and its password (optional) oneuser chauth "
        "my_user core oneuser chauth my_user core new_password oneuser chauth my_user "
        "core -r /tmp/mypass oneuser chauth my_user --ssh --key "
        "/home/oneadmin/.ssh/id_rsa oneuser chauth my_user --ssh -r /tmp/public_key "
        "oneuser chauth my_user --x509 --cert /tmp/my_cert.pem",
        "chgrp": "Changes the User's primary group",
        "create": "Creates a new User oneuser create my_user my_password oneuser create my_user "
        "-r /tmp/mypass oneuser create my_user my_password --group users,102,testers "
        "oneuser create my_user --ssh --key /tmp/id_rsa oneuser create my_user --ssh "
        "-r /tmp/public_key oneuser create my_user --x509 --cert /tmp/my_cert.pem "
        "oneuser create my_user --driver ldap",
        "defaultquota": "Sets the default quota limits for the users.",
        "delete": "Deletes the given User",
        "delgroup": "Removes the User from a secondary group",
        "disable": "Disables the given User",
        "enable": "Enables the given User",
        "encode": "Encodes user and password to use it with ldap",
        "key": "Shows a public key from a private SSH key.",
        "list": "Lists Users in the pool.",
        "login": "Alias of token-create.",
        "passwd": "Changes the given User's password",
        "passwdsearch": "Searches for users with a specific auth driver that has the given "
        "string in their password field",
        "quota": "Set the quota limits for the user.",
        "show": "Shows information for the given User",
        "token-create": "Creates the login token for authentication.",
        "token-delete": "Expires a token and removes the associated ONE_AUTH file if present.",
        "token-delete-all": "Delete all the tokens of a user.",
        "token-set": "Generates a ONE_AUTH file that contains the token.",
        "umask": "Changes the umask used to create the default permissions.",
        "update": "Update the template contents.",
    },
    "vdc": {
        "addcluster": "Adds a Cluster (from a specific Zone) to the given VDC",
        "adddatastore": "Adds a Datastore (from a specific Zone) to the given VDC",
        "addgroup": "Adds a Group to the given VDC",
        "addhost": "Adds a Host (from a specific Zone) to the given VDC",
        "addvnet": "Adds a Virtual Network (from a specific Zone) to the given VDC",
        "create": "Creates a new VDC",
        "delcluster": "Deletes a Cluster (from a specific Zone) from the given VDC",
        "deldatastore": "Deletes a Datastore (from a specific Zone) from the given VDC",
        "delete": "Deletes the given VDC",
        "delgroup": "Deletes a Group from the given VDC",
        "delhost": "Deletes a Host (from a specific Zone) from the given VDC",
        "delvnet": "Deletes a Virtual Network (from a specific Zone) from the given VDC",
        "list": "Lists VDCs in the pool.",
        "rename": "Renames the VDC",
        "show": "Shows information for the given VDC",
        "update": "Update the template contents.",
    },
    "vm": {
        "backup": "Creates a VM backup on the given datastore States: RUNNING, POWEROFF",
        "backup-cancel": "Cancels an active VM backup operation States: RUNNING, POWEROFF",
        "backupmode": "Updates the backup mode of a VM.",
        "chgrp": "Changes the VM group",
        "chmod": "Changes the VM permissions",
        "chown": "Changes the VM owner and group",
        "create": "Creates a new VM from the given description instead of using a previously "
        "defined template (see 'onetemplate create' and 'onetemplate instantiate').",
        "create-chart": "Adds a charter to the VM, these are some consecutive scheduled actions "
        "You can configure the actions in onevm.yaml",
        "delete-chart": "Deletes a charter from the VM Deprecated, use sched-delete instead",
        "deploy": "Deploys the given VM in the specified Host.",
        "disk-attach": "Attaches a disk to a running VM.",
        "disk-detach": "Detaches a disk from a running VM States: RUNNING, POWEROFF",
        "disk-resize": "Resizes a VM disk.",
        "disk-saveas": "Saves the specified VM disk as a new Image.",
        "disk-snapshot-create": "Takes a new snapshot of the given disk.",
        "disk-snapshot-delete": "Deletes a disk snapshot.",
        "disk-snapshot-list": "Lists the snapshots of a disk",
        "disk-snapshot-rename": "Renames a disk snapshot.",
        "disk-snapshot-revert": "Reverts disk state to a previously taken snapshot.",
        "hold": "Sets the given VM on hold.",
        "list": "Lists VMs in the pool.",
        "lock": "Locks a VM to prevent certain actions defined by different levels.",
        "migrate": "Migrates the given running VM to another Host.",
        "nic-attach": "Attaches a NIC to a VM.",
        "nic-detach": "Detaches a NIC from a running VM States: RUNNING, POWEROFF",
        "nic-update": "Updates a NIC for a VM.",
        "pci-attach": "Attaches a PCI to a VM.",
        "pci-detach": "Detaches a PCI device from a VM States: POWEROFF",
        "port-forward": "Get port forwarding from a NIC, e.g: 1.2.3.4@4000 -> 1, means that to "
        "connect to VM port 1, you need to connect to IP 1.2.3.4 in port 4000",
        "poweroff": "Powers off the given VM.",
        "reboot": "Reboots the given VM, this is equivalent to execute the reboot command from the "
        "VM console.",
        "recover": "Recovers a stuck VM that is waiting for a driver operation.",
        "release": "Releases a VM on hold.",
        "rename": "Renames the VM",
        "resched": "Sets the rescheduling flag for the VM.",
        "resize": "Resizes the capacity of a Virtual Machine A template can be passed as a file "
        "with or the content via STDIN Bash symbols must be escaped on STDIN passing",
        "restore": "Restore the Virtual Machine from the backup Image.",
        "resume": "Resumes the execution of a saved VM States: STOPPED, SUSPENDED, UNDEPLOYED, "
        "POWEROFF, UNKNOWN",
        "save": "Clones the VM's source Template, replacing the disks with live snapshots of the "
        "current disks.",
        "sched-delete": "Deletes a Scheduled Action from the VM",
        "sched-update": "Updates a Scheduled Action from a VM",
        "sg-attach": "Attaches a Security Group to a VM.",
        "sg-detach": "Detaches a Security Group from a VM.",
        "show": "Shows information for the given VM",
        "snapshot-create": "Creates a new VM snapshot",
        "snapshot-delete": "Delets a snapshot of a VM",
        "snapshot-list": "Lists the snapshots of a VM",
        "snapshot-revert": "Reverts a VM to a saved snapshot",
        "ssh": "SSH into VM Options example: '-o StrictHostKeyChecking=no -o "
        "UserKnownHostsFile=/dev/null'",
        "stop": "Stops a running VM.",
        "suspend": "Saves a running VM.",
        "terminate": "Terminates the given VM.",
        "top": "Lists Images continuously",
        "undeploy": "Shuts down the given VM.",
        "unlock": "Unlocks a Virtual Machine.",
        "unresched": "Clears the rescheduling flag for the VM.",
        "update": "Update the user template contents.",
        "update-chart": "Updates a charter from a VM Deprecated, use sched-update instead",
        "updateconf": "Updates the configuration of a VM.",
        "vnc": "Opens a VNC session to the VM",
    },
    "vmgroup": {
        "chgrp": "Changes the VM Group's group",
        "chmod": "Changes the VM Group permissions",
        "chown": "Changes the VM Group's owner and group",
        "create": "Creates a new VM Group from the given description",
        "delete": "Deletes the VM Group",
        "list": "Lists VM Group in the pool.",
        "lock": "Locks a VM Group to prevent certain actions defined by different levels.",
        "rename": "Renames the VM Group",
        "role-add": "Add role to VM Group.",
        "role-delete": "Deletes role from VM Group.",
        "role-update": "Update VM Group role",
        "show": "Shows information for the given VM Group",
        "unlock": "Unlocks a VM Group.",
        "update": "Update the template contents.",
    },
    "vnet": {
        "addar": "Adds an address range to the Virtual Network",
        "addleases": "(DEPRECATED, use addar) Adds a lease to the Virtual Network",
        "chgrp": "Changes the Virtual Network group",
        "chmod": "Changes the Virtual Network permissions",
        "chown": "Changes the Virtual Network owner and group",
        "create": "Creates a new Virtual Network from the given template A template can be "
        "passed as a file with or the content via STDIN Bash symbols must be escaped "
        "on STDIN passing",
        "delete": "Deletes the given Virtual Network",
        "free": "Frees a reserved address range from the Virtual Network",
        "hold": "Holds a Virtual Network lease, marking it as used",
        "list": "Lists Virtual Networks in the pool.",
        "lock": "Locks a Virtual Network to prevent certain actions defined by different levels.",
        "orphans": "Shows orphans vnets (i.e vnets not referenced in any template).",
        "recover": "Recovers a Virtual Network in ERROR state or waiting for a driver operation "
        "to complete.",
        "release": "Releases a Virtual Network lease on hold",
        "rename": "Renames the Virtual Network",
        "reserve": "Reserve addresses from the Virtual Network.",
        "rmar": "Removes an address range from the Virtual Network",
        "rmleases": "(DEPRECATED, use rmar) Removes a lease from the Virtual Network",
        "show": "Shows information for the given Virtual Network",
        "unlock": "Unlocks a Virtual Network.",
        "update": "Update the template contents.",
        "updatear": "Update Address Range variables.",
    },
    "vntemplate": {
        "chgrp": "Changes the VN Template group",
        "chmod": "Changes the VN Template permissions",
        "chown": "Changes the VN Template owner and group",
        "clone": "Creates a new VN Template from an existing one",
        "create": "Creates a new Virtual Network Template from the given description - "
        "using a Virtual Network Template description file: onevntemplate create "
        "vn_description.tmpl - using a Virtual Network Template description file "
        "via stdin: cat $vn_template | onevntemplate create",
        "delete": "Deletes the given VN Template",
        "instantiate": "Creates a new VN instance from the given VN Template.",
        "list": "Lists VN Templates in the pool.",
        "lock": "Locks a VN Template to prevent certain actions defined by different levels.",
        "rename": "Renames the VN Template",
        "show": "Shows information for the given VN Template",
        "top": "Lists Templates continuously",
        "unlock": "Unlocks a VN Template.",
        "update": "Update the VN template contents.",
    },
    "vrouter": {
        "chgrp": "Changes the Virtual Router group",
        "chmod": "Changes the Virtual Router permissions",
        "chown": "Changes the Virtual Router owner and group",
        "create": "Creates a new Virtual Router from the given description A template can be "
        "passed as a file with or the content via STDIN Bash symbols must be "
        "escaped on STDIN passing",
        "delete": "Deletes the given Virtual Router",
        "instantiate": "Creates a new VM instance from the given Template.",
        "list": "Lists the Virtual Routers in the pool.",
        "lock": "Locks a Virtual Router to prevent certain actions defined by different levels.",
        "nic-attach": "Attaches a NIC to a VirtualRouter, and each one of its VMs.",
        "nic-detach": "Detaches a NIC from a VirtualRouter, and each one of its VMs",
        "rename": "Renames the Virtual Router",
        "show": "Shows information for the given Virtual Router",
        "top": "Lists Virtual Routers continuously",
        "unlock": "Unlocks a Virtual Router.",
        "update": "Update the Virtual Router contents.",
    },
    "zone": {
        "create": "Creates a new Zone",
        "delete": "Deletes the given Zone",
        "disable": "Disable zone, disabled zones can execute only readonly commands",
        "enable": "Enable zone",
        "list": "Lists Zones in the pool.",
        "rename": "Renames the Zone",
        "server-add": "Add an OpenNebula server to this zone.",
        "server-del": "Delete an OpenNebula server from this zone.",
        "server-reset": "Reset follower log index.",
        "serversync": "Syncs configuration files and folders from another server This command "
        "must be executed under root",
        "set": "Set shell session access point for the CLI to the given Zone",
        "show": "Shows information for the given Zone",
        "update": "Update the template contents.",
    },
}


def official_command_description(family: str, command_name: str) -> str | None:
    """Return the official one-line description for a family command when available."""

    return OFFICIAL_COMMAND_DESCRIPTIONS.get(family, {}).get(command_name)
