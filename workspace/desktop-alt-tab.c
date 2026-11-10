/* Fast, one-shot notification for the preloaded switcher. No input hooks. */
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc,char **argv) {
    int reverse=argc>1&&!strcmp(argv[1],"--reverse");
    const char *runtime=getenv("XDG_RUNTIME_DIR");
    if(!runtime)runtime="/tmp";
    struct sockaddr_un address={.sun_family=AF_UNIX};
    int n=snprintf(address.sun_path,sizeof address.sun_path,"%s/desktop-alt-tab-warm.sock",runtime);
    if(n<0||(size_t)n>=sizeof address.sun_path)return 1;
    int fd=socket(AF_UNIX,SOCK_DGRAM|SOCK_CLOEXEC,0);
    if(fd>=0) {
        const char *message=reverse?"prev":"next";
        ssize_t sent=sendto(fd,message,4,0,(struct sockaddr*)&address,sizeof address);
        close(fd);
        if(sent==4)return 0;
    }
    /* Only a cold/missing service needs the Python startup fallback. */
    char executable[PATH_MAX],fallback[PATH_MAX];
    ssize_t len=readlink("/proc/self/exe",executable,sizeof executable-1);
    if(len<0)return 1;
    executable[len]=0;
    char *slash=strrchr(executable,'/');if(!slash)return 1;*slash=0;
    n=snprintf(fallback,sizeof fallback,"%s/desktop-alt-tab-client.py",executable);
    if(n<0||(size_t)n>=sizeof fallback)return 1;
    if(reverse)execl("/usr/bin/python3","python3",fallback,"--reverse",(char*)0);
    else execl("/usr/bin/python3","python3",fallback,(char*)0);
    perror("desktop-alt-tab");return 1;
}
