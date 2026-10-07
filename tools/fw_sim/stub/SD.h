// SD (arduino-libraries/SD 1.2.4) — bản giả: thẻ nhớ = 1 thư mục trên PC (sim_core: sim_sd_path).
#pragma once
#include "Arduino.h"

#define FILE_READ 0x01
#define FILE_WRITE 0x13  // đọc + ghi + tạo + nối cuối (giống SD lib)
#define O_READ 0x01
#define O_WRITE 0x02
#define O_CREAT 0x10
#define O_APPEND 0x04
#define O_TRUNC 0x40

std::string sim_sd_path(const char *p);

class File : public Stream {
  public:
    FILE *fp = nullptr;
    std::string nm;
    File() {}
    File(FILE *f, const char *n) : fp(f), nm(n ? n : "") {}
    operator bool() const { return fp != nullptr; }
    using Print::write;
    size_t write(uint8_t b) override { return fp ? fwrite(&b, 1, 1, fp) : 0; }
    size_t write(const uint8_t *buf, size_t n) override { return fp ? fwrite(buf, 1, n, fp) : 0; }
    int available() override
    {
        if (!fp)
            return 0;
        long cur = ftell(fp);
        fseek(fp, 0, SEEK_END);
        long end = ftell(fp);
        fseek(fp, cur, SEEK_SET);
        long d = end - cur;
        return d > 0x7fff ? 0x7fff : (int)d;
    }
    int read() override
    {
        if (!fp)
            return -1;
        int c = fgetc(fp);
        return c == EOF ? -1 : c;
    }
    int read(void *buf, size_t n) { return fp ? (int)fread(buf, 1, n, fp) : -1; }
    int peek() override
    {
        if (!fp)
            return -1;
        int c = fgetc(fp);
        if (c != EOF)
            ungetc(c, fp);
        return c == EOF ? -1 : c;
    }
    void flush() override
    {
        if (fp)
            fflush(fp);
    }
    bool seek(uint32_t pos) { return fp && fseek(fp, (long)pos, SEEK_SET) == 0; }
    uint32_t position() { return fp ? (uint32_t)ftell(fp) : 0; }
    uint32_t size()
    {
        if (!fp)
            return 0;
        long cur = ftell(fp);
        fseek(fp, 0, SEEK_END);
        long end = ftell(fp);
        fseek(fp, cur, SEEK_SET);
        return (uint32_t)end;
    }
    void close()
    {
        if (fp)
            fclose(fp);
        fp = nullptr;
    }
    const char *name() const { return nm.c_str(); }
    bool isDirectory() const { return false; }
    File openNextFile(uint8_t = O_READ) { return File(); }
    void rewindDirectory() {}
};

class SDClass {
  public:
    bool begin(uint8_t cs = 0) { (void)cs; return true; }
    bool begin(uint32_t clock, uint8_t cs) { (void)clock; (void)cs; return true; }
    File open(const char *path, uint8_t mode = FILE_READ)
    {
        std::string p = sim_sd_path(path);
        FILE *f = nullptr;
        if (mode == FILE_READ) {
            f = fopen(p.c_str(), "rb");
        } else {
            f = fopen(p.c_str(), "r+b");
            if (!f)
                f = fopen(p.c_str(), "w+b");
            if (f && (mode & O_APPEND || mode == FILE_WRITE))
                fseek(f, 0, SEEK_END);
            if (f && (mode & O_TRUNC)) {
                fclose(f);
                f = fopen(p.c_str(), "w+b");
            }
        }
        return File(f, path);
    }
    File open(const String &path, uint8_t mode = FILE_READ) { return open(path.c_str(), mode); }
    bool exists(const char *path)
    {
        FILE *f = fopen(sim_sd_path(path).c_str(), "rb");
        if (f)
            fclose(f);
        return f != nullptr;
    }
    bool exists(const String &p) { return exists(p.c_str()); }
    bool remove(const char *path) { return ::remove(sim_sd_path(path).c_str()) == 0; }
    bool remove(const String &p) { return remove(p.c_str()); }
    bool mkdir(const char *) { return true; }
    bool rmdir(const char *) { return true; }
};

extern SDClass SD;
