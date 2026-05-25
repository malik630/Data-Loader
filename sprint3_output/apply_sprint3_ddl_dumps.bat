@echo off
:: =============================================================
:: apply_sprint3_ddl_dumps.bat — Sprint 3 Team 3 | Topic M6 | Team SG03
:: Applies Sprint 3 DDL + dumps on top of existing Sprint 2 DBs
:: Prerequisites: m6_thermal and m6_thermal_tsdb already exist
:: =============================================================

:: ── PostgreSQL config ─────────────────────────────────────────
set PG_HOST=localhost
set PG_PORT=5432
set PG_USER=postgres
set PG_PASSWORD=postgres
set PG_DB=m6_thermal

:: ── TimescaleDB config ────────────────────────────────────────
set TSDB_HOST=localhost
set TSDB_PORT=5433
set TSDB_USER=postgres
set TSDB_PASSWORD=postgres
set TSDB_DB=m6_thermal_tsdb

:: ─────────────────────────────────────────────────────────────

echo.
echo =====================================================
echo  Sprint 3 - DB Setup (DDL + Dumps)
echo =====================================================

echo.
echo [1/4] Applying PostgreSQL DDL (new tables Sprint 3)...
set PGPASSWORD=%PG_PASSWORD%
psql -h %PG_HOST% -p %PG_PORT% -U %PG_USER% -d %PG_DB% -f schema_postgres.sql
if %ERRORLEVEL% NEQ 0 ( echo ERROR on schema_postgres.sql & pause & exit /b 1 )

echo.
echo [2/4] Applying TimescaleDB DDL (new tables Sprint 3)...
set PGPASSWORD=%TSDB_PASSWORD%
psql -h %TSDB_HOST% -p %TSDB_PORT% -U %TSDB_USER% -d %TSDB_DB% -f schema_timescaledb.sql
if %ERRORLEVEL% NEQ 0 ( echo ERROR on schema_timescaledb.sql & pause & exit /b 1 )

echo.
echo [3/4] Inserting Sprint 3 sample data (PostgreSQL)...
set PGPASSWORD=%PG_PASSWORD%
psql -h %PG_HOST% -p %PG_PORT% -U %PG_USER% -d %PG_DB% -f sample_dump_postgres.sql
if %ERRORLEVEL% NEQ 0 ( echo ERROR on sample_dump_postgres.sql & pause & exit /b 1 )

echo.
echo [4/4] Inserting Sprint 3 sample data (TimescaleDB)...
set PGPASSWORD=%TSDB_PASSWORD%
psql -h %TSDB_HOST% -p %TSDB_PORT% -U %TSDB_USER% -d %TSDB_DB% -f sample_dump_timescaledb.sql
if %ERRORLEVEL% NEQ 0 ( echo ERROR on sample_dump_timescaledb.sql & pause & exit /b 1 )

echo.
echo =====================================================
echo  Done! Sprint 3 data applied successfully.
echo =====================================================
echo.
pause