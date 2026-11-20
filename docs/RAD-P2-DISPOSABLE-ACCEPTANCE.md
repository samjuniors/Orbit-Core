# RAD P2 disposable Windows LPAC acceptance

[Issue #138](https://github.com/samjuniors/Orbit-Core/issues/138) tracks OS isolation acceptance. Run this procedure manually in an authorized local Windows session with trusted CPython 3.12 or later and an existing x64 MSVC Developer Command Prompt with the Windows SDK. Each run provisions one disposable profile and limits ACL changes to newly created synthetic directories.

## Scope

The harness builds the reviewed `scripts/rad_p2_disposable_probe.c` using the installed compiler and SDK. An environment-supplied `ORBIT_PROBE_EXECUTABLE` is explicitly rejected: an arbitrary binary could forge native denial results. The acceptance JSON records independent SHA-256 values for the C source and compiled probe. If the exact reviewed source cannot be built with the trusted MSVC SDK, record BLOCKED rather than silently selecting another executable. The native probe uses Windows APIs directly and requires no C runtime DLL. The new profile SID gets traverse access on the generated root, read and execute access on the probe, and modify access on the synthetic project. Low integrity applies to the synthetic project only. Separate sibling-project and fake-credential files receive no grants. The only network targets are a private listener on 127.0.0.1 and an IPv4 TCP handshake to 1.1.1.1 port 443. The handshake carries no application data.

## Run

The default command prints a non-mutating plan and exits 2.

    py -3.12 scripts/rad_p2_disposable_host_acceptance.py

Inspect both source files and use the local session's native permission controls for the authorized run.

    py -3.12 scripts/rad_p2_disposable_host_acceptance.py --apply --confirm "CREATE DISPOSABLE ORBIT APPCONTAINER"

Add `--python-startup` to compare the same staged base CPython and synthetic startup marker under the host and LPAC. The diagnostic reads from the trusted local interpreter, copies only the base runtime and standard library into the disposable fixture, and records both process exit codes. The staging process neutralizes the embedded `RT_MANIFEST` resource in the staged copy of the CPython DLL, preventing the Windows CSRSS activation context creation error (`0xC0000022`) inside LPAC without modifying host files or granting extra capabilities. This checks interpreter startup. Python web preview has separate socket and endpoint ownership gates.

Add `--diagnose-resources` to compare read-only WinSock catalog opens and provider DLL loading. With `--python-startup`, it also compares opening and loading the exact staged CPython DLL. The report contains the native exit code for each operation both outside and inside LPAC. The same option interrupts a separate fixture controller and waits on the exact child process handle to verify cleanup. Catalog checks request access to fixed Windows keys without reading values or making registry changes.

Add `--capability-registry-read` to evaluate Winsock catalog access and network denial using Microsoft's standard LPAC `registryRead` capability SID (`S-1-15-3-1024-1065365936-1281604716-3511738428-1654721687-432734479-3232135806-4053264122-3456934681`). Under pure zero-capability LPAC, `Protocol_Catalog9` and `NameSpace_Catalog5` registry reads are denied by OS policy (error 5), producing Winsock error `10107`. With `registryRead`, `WSAStartup` succeeds (0), and subsequent socket/connect calls are denied with `WSAEACCES` (`10013`) by Windows Filtering Platform due to the absence of network capabilities (`internetClient`, `privateNetworkClientServer`).

The script emits the generated root and profile name on stderr before provisioning. A separate line records successful creation. Keep both lines and the final JSON. Exit code 2 keeps the overall outcome on hold for review of the individual checks.

## Read the evidence

- The launcher checks the suspended process's AppContainer token, exact package SID, zero effective token capabilities, and membership in the private Job Object. An in-memory Windows access check on the child token must grant the right for restricted application packages while denying the right for all application packages. These checks all precede resume.
- The child reads known project content and writes a marker verified by the parent. File denial requires Windows error 5 with a working positive control. A missing file or missing child output leaves the check unverified.
- Each network check requires successful Winsock startup in the same native binary outside LPAC, a successful parent connection, and Winsock error 10013 from the LPAC child on the same endpoint. A Winsock startup failure blocks both endpoint tests. A timeout or unavailable endpoint leaves that check unverified. A successful LPAC connection fails the check.
- When the probe can start a descendant, the controller verifies its job membership by process handle and waits for the descendant to exit after job termination. The controller also verifies termination of two directly launched LPAC members. A separate job measures a forced child exit followed by a replacement launch using the same profile.

## Cleanup and recovery

The result records the profile deletion HRESULT, absence of the Windows-reported profile storage path, and absence of the exact test root containing the ACL fixtures. Verify each result separately. A controller crash before cleanup can leave the profile or fixtures. Reconcile only the exact identifiers logged by this invocation. Delete a profile only if the run recorded successful creation of that profile. For profile removal, use the documented [DeleteAppContainerProfile API](https://learn.microsoft.com/en-us/windows/win32/api/userenv/nf-userenv-deleteappcontainerprofile) under the same user account after the job has exited.

Host approval and denial, additional filesystem and registry boundaries, private-network scope, and independent security review remain tracked in issue #138. Keep this runner manual and outside CI and installer hooks.
