// Lớp String kiểu Arduino (tập con firmware OTL dùng), lõi là std::string.
#pragma once

class String {
  public:
    std::string s;

    String() {}
    String(const char *c) : s(c ? c : "") {}
    String(const std::string &x) : s(x) {}
    String(const String &o) = default;
    String &operator=(const String &o) = default;
    explicit String(char c) : s(1, c) {}
    String(int v, unsigned char base = 10) { s = num(v, base); }
    String(unsigned int v, unsigned char base = 10) { s = unum(v, base); }
    String(long v, unsigned char base = 10) { s = num(v, base); }
    String(unsigned long v, unsigned char base = 10) { s = unum(v, base); }
    String(float v, unsigned char dec = 2) { s = flt(v, dec); }
    String(double v, unsigned char dec = 2) { s = flt(v, dec); }

    static std::string num(long v, unsigned char base)
    {
        if (base == 10) {
            char b[32];
            snprintf(b, sizeof(b), "%ld", v);
            return b;
        }
        return unum((unsigned long)v, base);
    }
    static std::string unum(unsigned long v, unsigned char base)
    {
        if (!base)
            base = 10;
        char b[72];
        int i = 70;
        b[71] = 0;
        if (v == 0)
            b[i--] = '0';
        while (v && i >= 0) {
            int d = (int)(v % base);
            b[i--] = (char)(d < 10 ? '0' + d : 'A' + d - 10);
            v /= base;
        }
        return std::string(b + i + 1);
    }
    static std::string flt(double v, unsigned char dec)
    {
        char b[64];
        snprintf(b, sizeof(b), "%.*f", (int)dec, v);
        return b;
    }

    const char *c_str() const { return s.c_str(); }
    unsigned int length() const { return (unsigned int)s.size(); }
    char charAt(unsigned int i) const { return i < s.size() ? s[i] : 0; }
    char operator[](unsigned int i) const { return charAt(i); }
    char &operator[](unsigned int i) { return s[i]; }
    void setCharAt(unsigned int i, char c)
    {
        if (i < s.size())
            s[i] = c;
    }

    String &operator+=(const String &o) { s += o.s; return *this; }
    String &operator+=(const char *c) { s += (c ? c : ""); return *this; }
    String &operator+=(char c) { s += c; return *this; }
    String &operator+=(int v) { s += num(v, 10); return *this; }
    String &operator+=(unsigned int v) { s += unum(v, 10); return *this; }
    String &operator+=(long v) { s += num(v, 10); return *this; }
    String &operator+=(unsigned long v) { s += unum(v, 10); return *this; }
    String &operator+=(float v) { s += flt(v, 2); return *this; }
    String &operator+=(double v) { s += flt(v, 2); return *this; }
    bool concat(const String &o) { s += o.s; return true; }
    bool concat(const char *c) { s += (c ? c : ""); return true; }
    bool concat(char c) { s += c; return true; }
    bool concat(int v) { s += num(v, 10); return true; }
    bool concat(float v) { s += flt(v, 2); return true; }

    bool operator==(const String &o) const { return s == o.s; }
    bool operator==(const char *c) const { return s == (c ? c : ""); }
    bool operator!=(const String &o) const { return s != o.s; }
    bool operator!=(const char *c) const { return s != (c ? c : ""); }
    bool operator<(const String &o) const { return s < o.s; }
    bool equals(const String &o) const { return s == o.s; }
    bool equalsIgnoreCase(const String &o) const
    {
        if (s.size() != o.s.size())
            return false;
        for (size_t i = 0; i < s.size(); i++)
            if (tolower((unsigned char)s[i]) != tolower((unsigned char)o.s[i]))
                return false;
        return true;
    }
    bool startsWith(const String &p) const { return s.compare(0, p.s.size(), p.s) == 0; }
    bool endsWith(const String &p) const
    {
        return s.size() >= p.s.size() && s.compare(s.size() - p.s.size(), p.s.size(), p.s) == 0;
    }
    int indexOf(char c, unsigned int from = 0) const
    {
        size_t p = s.find(c, from);
        return p == std::string::npos ? -1 : (int)p;
    }
    int indexOf(const String &x, unsigned int from = 0) const
    {
        size_t p = s.find(x.s, from);
        return p == std::string::npos ? -1 : (int)p;
    }
    int lastIndexOf(char c) const
    {
        size_t p = s.rfind(c);
        return p == std::string::npos ? -1 : (int)p;
    }
    String substring(unsigned int from) const { return from < s.size() ? String(s.substr(from)) : String(); }
    String substring(unsigned int from, unsigned int to) const
    {
        if (from > to)
            std::swap(from, to);
        if (from >= s.size())
            return String();
        return String(s.substr(from, to - from));
    }
    void trim()
    {
        size_t a = s.find_first_not_of(" \t\r\n");
        size_t b = s.find_last_not_of(" \t\r\n");
        s = (a == std::string::npos) ? std::string() : s.substr(a, b - a + 1);
    }
    void toUpperCase()
    {
        for (auto &c : s)
            c = (char)toupper((unsigned char)c);
    }
    void toLowerCase()
    {
        for (auto &c : s)
            c = (char)tolower((unsigned char)c);
    }
    void replace(const String &a, const String &b)
    {
        if (a.s.empty())
            return;
        size_t p = 0;
        while ((p = s.find(a.s, p)) != std::string::npos) {
            s.replace(p, a.s.size(), b.s);
            p += b.s.size();
        }
    }
    void remove(unsigned int idx) { if (idx < s.size()) s.erase(idx); }
    void remove(unsigned int idx, unsigned int n) { if (idx < s.size()) s.erase(idx, n); }
    long toInt() const { return atol(s.c_str()); }
    float toFloat() const { return (float)atof(s.c_str()); }
    double toDouble() const { return atof(s.c_str()); }
    void reserve(unsigned int n) { s.reserve(n); }
    void toCharArray(char *buf, unsigned int n) const
    {
        if (!n)
            return;
        strncpy(buf, s.c_str(), n - 1);
        buf[n - 1] = 0;
    }
    void getBytes(unsigned char *buf, unsigned int n) const { toCharArray((char *)buf, n); }
};

inline String operator+(const String &a, const String &b) { String r(a); r += b; return r; }
inline String operator+(const String &a, const char *b) { String r(a); r += b; return r; }
inline String operator+(const char *a, const String &b) { String r(a); r += b; return r; }
inline String operator+(const String &a, char b) { String r(a); r += b; return r; }
inline String operator+(const String &a, int b) { String r(a); r += b; return r; }
inline String operator+(const String &a, unsigned int b) { String r(a); r += b; return r; }
inline String operator+(const String &a, long b) { String r(a); r += b; return r; }
inline String operator+(const String &a, unsigned long b) { String r(a); r += b; return r; }
inline String operator+(const String &a, float b) { String r(a); r += b; return r; }
inline String operator+(const String &a, double b) { String r(a); r += b; return r; }
inline bool operator==(const char *a, const String &b) { return b == a; }
