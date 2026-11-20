/* Disposable fixture probe. Uses only Windows system APIs and no CRT DLL. */
#define WIN32_LEAN_AND_MEAN
#include <winsock2.h>
#include <windows.h>

/* MSVC can emit memset for aggregate initialization even without a CRT. */
#pragma function(memset)
void *memset(void *destination, int value, size_t size)
{
    volatile unsigned char *bytes = destination;
    while (size--)
        *bytes++ = (unsigned char)value;
    return destination;
}

struct observations {
    DWORD allowed_read, allowed_write, sibling_read, sibling_write;
    DWORD credential_read, winsock_startup, loopback, external;
    DWORD descendant_pid, descendant_error;
};

static WCHAR image[4096];
static WCHAR descendant_command[4096];

static DWORD read_fixture(const WCHAR *path, const char *expected)
{
    HANDLE file = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, 0, NULL);
    char data[64] = {0};
    DWORD size = 0;
    if (file == INVALID_HANDLE_VALUE)
        return GetLastError();
    DWORD error = ReadFile(file, data, sizeof(data) - 1, &size, NULL) ? 0 : GetLastError();
    CloseHandle(file);
    if (!error && expected != NULL &&
        (size != (DWORD)lstrlenA(expected) || lstrcmpA(data, expected) != 0))
        return ERROR_INVALID_DATA;
    return error;
}

static DWORD write_fixture(const WCHAR *path, DWORD disposition, const void *data, DWORD size)
{
    HANDLE file = CreateFileW(path, GENERIC_WRITE, FILE_SHARE_READ, NULL, disposition, 0, NULL);
    if (file == INVALID_HANDLE_VALUE)
        return GetLastError();
    DWORD written = 0;
    DWORD error = WriteFile(file, data, size, &written, NULL) ? 0 : GetLastError();
    CloseHandle(file);
    return !error && written != size ? ERROR_WRITE_FAULT : error;
}

static DWORD connect_endpoint(unsigned long address, unsigned short port)
{
    SOCKET client = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (client == INVALID_SOCKET)
        return (DWORD)WSAGetLastError();
    struct sockaddr_in endpoint = {0};
    endpoint.sin_family = AF_INET;
    endpoint.sin_addr.s_addr = htonl(address);
    endpoint.sin_port = htons(port);
    unsigned long nonblocking = 1;
    DWORD error = ERROR_NOT_READY;
    if (ioctlsocket(client, FIONBIO, &nonblocking) == 0) {
        if (connect(client, (const struct sockaddr *)&endpoint, sizeof(endpoint)) == 0) {
            error = 0;
        } else {
            error = (DWORD)WSAGetLastError();
            if (error == WSAEWOULDBLOCK) {
                fd_set writable, failed;
                FD_ZERO(&writable);
                FD_ZERO(&failed);
                FD_SET(client, &writable);
                FD_SET(client, &failed);
                struct timeval timeout = {2, 0};
                int selected = select(0, NULL, &writable, &failed, &timeout);
                int socket_error = 0, size = sizeof(socket_error);
                if (selected > 0 && getsockopt(client, SOL_SOCKET, SO_ERROR,
                                              (char *)&socket_error, &size) == 0)
                    error = (DWORD)socket_error;
                else
                    error = selected == 0 ? WSAETIMEDOUT : ERROR_NOT_READY;
            }
        }
    }
    closesocket(client);
    return error;
}

static DWORD start_descendant(DWORD *pid)
{
    DWORD length = GetModuleFileNameW(NULL, image, ARRAYSIZE(image));
    if (!length || length >= ARRAYSIZE(image) - 16)
        return ERROR_BAD_PATHNAME;
    lstrcpyW(descendant_command, L"\"");
    lstrcatW(descendant_command, image);
    lstrcatW(descendant_command, L"\" descendant");
    STARTUPINFOW startup = {0};
    PROCESS_INFORMATION process = {0};
    startup.cb = sizeof(startup);
    if (!CreateProcessW(image, descendant_command, NULL, NULL, FALSE, CREATE_NO_WINDOW,
                        NULL, NULL, &startup, &process))
        return GetLastError();
    *pid = process.dwProcessId;
    CloseHandle(process.hThread);
    CloseHandle(process.hProcess);
    return 0;
}

static const WCHAR *mode(void)
{
    const WCHAR *command = GetCommandLineW();
    if (*command == L'"') {
        ++command;
        while (*command && *command != L'"')
            ++command;
        if (*command)
            ++command;
    } else {
        while (*command && *command != L' ')
            ++command;
    }
    while (*command == L' ')
        ++command;
    return command;
}

static DWORD open_catalog(const WCHAR *path)
{
    HKEY catalog;
    LSTATUS status = RegOpenKeyExW(HKEY_LOCAL_MACHINE, path, 0, KEY_QUERY_VALUE, &catalog);
    if (!status)
        RegCloseKey(catalog);
    return (DWORD)status;
}

static DWORD load_module(const WCHAR *path, DWORD flags)
{
    HMODULE module = LoadLibraryExW(path, NULL, flags);
    if (!module)
        return GetLastError();
    FreeLibrary(module);
    return ERROR_SUCCESS;
}

static DWORD python_module(const WCHAR *abi, BOOL load)
{
    DWORD digits = (DWORD)lstrlenW(abi);
    if (digits < 2 || digits > 4)
        return ERROR_INVALID_PARAMETER;
    for (DWORD i = 0; i < digits; i++) {
        if (abi[i] < L'0' || abi[i] > L'9')
            return ERROR_INVALID_PARAMETER;
    }
    DWORD length = GetModuleFileNameW(NULL, image, ARRAYSIZE(image));
    if (!length || length >= ARRAYSIZE(image) - 32)
        return ERROR_BAD_PATHNAME;
    while (length && image[length - 1] != L'\\')
        --length;
    if (!length)
        return ERROR_BAD_PATHNAME;
    image[length] = L'\0';
    lstrcatW(image, L"python\\python");
    lstrcatW(image, abi);
    lstrcatW(image, L".dll");
    if (load)
        return load_module(image, LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_SYSTEM32);
    HANDLE file = CreateFileW(image, GENERIC_READ | FILE_EXECUTE, FILE_SHARE_READ,
                              NULL, OPEN_EXISTING, 0, NULL);
    if (file == INVALID_HANDLE_VALUE)
        return GetLastError();
    CloseHandle(file);
    return ERROR_SUCCESS;
}

void __cdecl probe_main(void)
{
    const WCHAR *argument = mode();
    if (lstrcmpW(argument, L"crash") == 0)
        ExitProcess(23);
    if (lstrcmpW(argument, L"recover") == 0)
        ExitProcess(0);
    if (lstrcmpW(argument, L"descendant") == 0) {
        Sleep(30000);
        ExitProcess(0);
    }
    if (lstrcmpW(argument, L"winsock-control") == 0) {
        WSADATA data;
        int error = WSAStartup(MAKEWORD(2, 2), &data);
        if (!error)
            WSACleanup();
        ExitProcess((UINT)error);
    }
    if (lstrcmpW(argument, L"winsock-protocol-key") == 0)
        ExitProcess(open_catalog(L"SYSTEM\\CurrentControlSet\\Services\\WinSock2\\Parameters\\Protocol_Catalog9"));
    if (lstrcmpW(argument, L"winsock-namespace-key") == 0)
        ExitProcess(open_catalog(L"SYSTEM\\CurrentControlSet\\Services\\WinSock2\\Parameters\\NameSpace_Catalog5"));
    if (lstrcmpW(argument, L"winsock-provider") == 0)
        ExitProcess(load_module(L"mswsock.dll", LOAD_LIBRARY_SEARCH_SYSTEM32));
    const WCHAR python_mode[] = L"python-dll ";
    int prefix = ARRAYSIZE(python_mode) - 1;
    if (lstrlenW(argument) > prefix &&
        CompareStringOrdinal(argument, prefix, python_mode, prefix, FALSE) == CSTR_EQUAL)
        ExitProcess(python_module(argument + prefix, TRUE));
    const WCHAR python_file_mode[] = L"python-file ";
    prefix = ARRAYSIZE(python_file_mode) - 1;
    if (lstrlenW(argument) > prefix &&
        CompareStringOrdinal(argument, prefix, python_file_mode, prefix, FALSE) == CSTR_EQUAL)
        ExitProcess(python_module(argument + prefix, FALSE));
    if (lstrcmpW(argument, L"probe") != 0)
        ExitProcess(ERROR_INVALID_PARAMETER);

    WCHAR port_text[6];
    DWORD length = GetEnvironmentVariableW(L"PORT", port_text, ARRAYSIZE(port_text));
    if (!length || length >= ARRAYSIZE(port_text))
        ExitProcess(ERROR_INVALID_PARAMETER);
    unsigned long port = 0;
    for (DWORD index = 0; index < length; ++index) {
        if (port_text[index] < L'0' || port_text[index] > L'9')
            ExitProcess(ERROR_INVALID_PARAMETER);
        port = port * 10 + (unsigned long)(port_text[index] - L'0');
    }
    if (!port || port > 65535)
        ExitProcess(ERROR_INVALID_PARAMETER);

    const WCHAR *sibling = L"..\\sibling\\project.txt";
    struct observations result = {0};
    result.allowed_read = read_fixture(L"allowed.txt", "ORBIT_ALLOWED");
    result.allowed_write = write_fixture(L"allowed.out", CREATE_NEW, "ORBIT_WRITTEN", 13);
    result.sibling_read = read_fixture(sibling, NULL);
    result.sibling_write = write_fixture(sibling, OPEN_EXISTING, "UNEXPECTED_WRITE", 16);
    result.credential_read = read_fixture(L"..\\credentials\\fake.txt", NULL);
    WSADATA winsock;
    result.winsock_startup = (DWORD)WSAStartup(MAKEWORD(2, 2), &winsock);
    if (!result.winsock_startup) {
        result.loopback = connect_endpoint(INADDR_LOOPBACK, (unsigned short)port);
        result.external = connect_endpoint(0x01010101, 443);
        WSACleanup();
    }
    result.descendant_error = start_descendant(&result.descendant_pid);
    DWORD error = write_fixture(L"result.tmp", CREATE_NEW, &result, sizeof(result));
    if (error)
        ExitProcess(error);
    if (!MoveFileW(L"result.tmp", L"result.bin"))
        ExitProcess(GetLastError());
    Sleep(30000);
    ExitProcess(0);
}
