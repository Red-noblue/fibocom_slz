// 中文说明：该兼容层用于在 QEMU user-mode 下运行 Fibo AI Stack x86_64 工具时，
// 将进程共享/优先级继承 mutex 属性降级为普通进程内 mutex，规避旧版 QEMU 对 PI futex 支持不足的问题。
#define _GNU_SOURCE

#include <dlfcn.h>
#include <pthread.h>

typedef int (*pthread_mutexattr_setpshared_fn)(pthread_mutexattr_t *, int);
typedef int (*pthread_mutexattr_setprotocol_fn)(pthread_mutexattr_t *, int);

int pthread_mutexattr_setpshared(pthread_mutexattr_t *attr, int pshared) {
  static pthread_mutexattr_setpshared_fn real_fn = NULL;
  (void)pshared;
  if (real_fn == NULL) {
    real_fn = (pthread_mutexattr_setpshared_fn)dlsym(RTLD_NEXT, "pthread_mutexattr_setpshared");
  }
  return real_fn(attr, PTHREAD_PROCESS_PRIVATE);
}

int pthread_mutexattr_setprotocol(pthread_mutexattr_t *attr, int protocol) {
  static pthread_mutexattr_setprotocol_fn real_fn = NULL;
  (void)protocol;
  if (real_fn == NULL) {
    real_fn = (pthread_mutexattr_setprotocol_fn)dlsym(RTLD_NEXT, "pthread_mutexattr_setprotocol");
  }
  return real_fn(attr, PTHREAD_PRIO_NONE);
}
