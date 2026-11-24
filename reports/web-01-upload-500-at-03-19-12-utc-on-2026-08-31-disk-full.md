# web-01 upload 500 at 03:19:12 UTC on 2026-08-31: disk full

- Severity: high
- Saved: 2026-11-24T11:26:02Z

At 03:19:12 UTC on 2026-08-31 a POST /upload from 172.18.0.12 got HTTP 500. PHP's file_put_contents() in /var/www/customer-site/upload.php line 14 failed with errno=28, "No space left on device". php-fpm passed the notice to nginx, which logged it as a FastCGI stderr error, and the customer got the error page. Earlier uploads on 2026-08-30 returned 200, and uploads from 05:48 on 2026-08-31 onward also returned 200, so the failure was a single event in the logs. The logs do not show which volume was full or what filled it, and nothing in web-01's syslog or auth logs around 03:19 explains it. nginx buffers large request bodies under /var/www/customer-site/uploads/nginx_tmp, which suggests uploads share the filesystem, but that is an inference. The next step is to check df and what is using space on web-01's volume around that time.

## Evidence

- `vms/web-01/archive/nginx-access-2026-08-31.log.gz` line 1: POST /upload from 172.18.0.12 returned 500 at 03:19:12
- `vms/web-01/archive/nginx-error-2026-08-31.log.gz` line 1: FastCGI stderr: file_put_contents() write failed, errno=28 No space left on device, upload.php line 14
- `vms/web-01/archive/php-fpm-2026-08-31.log.gz` line 6: php-fpm child 32 reported the same ENOSPC write failure
- `vms/web-01/archive/nginx-access-2026-08-31.log.gz` line 2: Next upload at 05:48:00 returned 200, so the condition was not persistent in the logs
