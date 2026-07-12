import { useEffect, useState, useCallback, useRef } from 'react';
import { apiClient } from '../api/client';

interface AttendanceRecord {
  id: number;
  student_id: number;
  name: string;
  timestamp: string;
  type: string;
  method: string;
}

interface AttendanceResponse {
  records: AttendanceRecord[];
  total: number;
  page: number;
  pages: number;
}

interface StudentsResponse {
  students: { id: number; name: string }[];
}

function getTodayISO(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export function Dashboard() {
  const [records, setRecords] = useState<AttendanceRecord[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);

  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [appliedFrom, setAppliedFrom] = useState('');
  const [appliedTo, setAppliedTo] = useState('');

  const [todayCount, setTodayCount] = useState<number | null>(null);
  const [studentCount, setStudentCount] = useState<number | null>(null);

  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  const fetchAttendance = useCallback(async (p: number, df: string, dt: string) => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = { page: p, limit: 10 };
      if (df) params.date_from = df;
      if (dt) params.date_to = dt;
      const res = await apiClient.get<AttendanceResponse>('/attendance', { params });
      if (mountedRef.current) {
        setRecords(res.data.records);
        setTotalPages(res.data.pages);
      }
    } catch {
      if (mountedRef.current) {
        setRecords([]);
        setTotalPages(1);
      }
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, []);

  const fetchSummary = useCallback(async () => {
    const today = getTodayISO();
    try {
      const [attRes, stuRes] = await Promise.all([
        apiClient.get<AttendanceResponse>('/attendance', {
          params: { date_from: today, date_to: today, page: 1, limit: 1 },
        }),
        apiClient.get<StudentsResponse>('/students'),
      ]);
      if (mountedRef.current) {
        setTodayCount(attRes.data.total);
        setStudentCount(stuRes.data.students.length);
      }
    } catch {
      if (mountedRef.current) {
        setTodayCount(0);
        setStudentCount(0);
      }
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchAttendance(page, appliedFrom, appliedTo);
  }, [page, appliedFrom, appliedTo, fetchAttendance]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchSummary();
  }, [fetchSummary]);

  const handleFilter = () => {
    setPage(1);
    setAppliedFrom(dateFrom);
    setAppliedTo(dateTo);
  };

  const handlePdfDownload = async () => {
    const params: Record<string, string> = {};
    if (appliedFrom) params.date_from = appliedFrom;
    if (appliedTo) params.date_to = appliedTo;
    try {
      const res = await apiClient.get('/report/pdf', {
        params,
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      const today = getTodayISO();
      link.setAttribute('download', `asistencia_${today}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      alert('Error downloading PDF');
    }
  };

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '32px 20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <h1 style={{ fontSize: 28, fontWeight: 700, color: 'var(--text-h)', margin: 0 }}>
          Dashboard
        </h1>
        <button
          type="button"
          onClick={handlePdfDownload}
          style={{
            padding: '8px 16px',
            borderRadius: 8,
            border: '1px solid var(--accent)',
            background: 'transparent',
            color: 'var(--accent)',
            fontSize: 14,
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          Descargar PDF
        </button>
      </div>

      <div style={{ display: 'flex', gap: 16, marginBottom: 28 }}>
        <div
          style={{
            flex: 1,
            padding: '20px 24px',
            borderRadius: 10,
            background: 'var(--accent-bg)',
            border: '1px solid var(--accent)',
          }}
        >
          <p style={{ fontSize: 13, color: 'var(--text)', margin: '0 0 4px' }}>Asistentes hoy</p>
          <p style={{ fontSize: 32, fontWeight: 700, color: 'var(--text-h)', margin: 0 }}>
            {todayCount !== null ? todayCount : '...'}
          </p>
        </div>
        <div
          style={{
            flex: 1,
            padding: '20px 24px',
            borderRadius: 10,
            background: 'var(--accent-bg)',
            border: '1px solid var(--accent)',
          }}
        >
          <p style={{ fontSize: 13, color: 'var(--text)', margin: '0 0 4px' }}>Estudiantes registrados</p>
          <p style={{ fontSize: 32, fontWeight: 700, color: 'var(--text-h)', margin: 0 }}>
            {studentCount !== null ? studentCount : '...'}
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 20, alignItems: 'flex-end' }}>
        <div>
          <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 4, color: 'var(--text-h)' }}>
            Desde
          </label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            style={{
              padding: '8px 10px',
              borderRadius: 6,
              border: '1px solid var(--border)',
              background: 'var(--bg)',
              color: 'var(--text-h)',
              fontSize: 14,
            }}
          />
        </div>
        <div>
          <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 4, color: 'var(--text-h)' }}>
            Hasta
          </label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            style={{
              padding: '8px 10px',
              borderRadius: 6,
              border: '1px solid var(--border)',
              background: 'var(--bg)',
              color: 'var(--text-h)',
              fontSize: 14,
            }}
          />
        </div>
        <button
          type="button"
          onClick={handleFilter}
          style={{
            padding: '8px 18px',
            borderRadius: 6,
            border: 'none',
            background: 'var(--accent)',
            color: '#fff',
            fontSize: 14,
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          Filtrar
        </button>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 40, color: 'var(--text)' }}>
          <div
            style={{
              display: 'inline-block',
              width: 28,
              height: 28,
              border: '3px solid var(--border)',
              borderTopColor: 'var(--accent)',
              borderRadius: '50%',
              animation: 'spin 0.8s linear infinite',
            }}
          />
          <p style={{ marginTop: 8 }}>Cargando registros...</p>
        </div>
      ) : records.length === 0 ? (
        <p style={{ textAlign: 'center', padding: 40, color: 'var(--text)' }}>
          No hay registros.
        </p>
      ) : (
        <table
          style={{
            width: '100%',
            borderCollapse: 'collapse',
            fontSize: 14,
          }}
        >
          <thead>
            <tr style={{ borderBottom: '2px solid var(--border)' }}>
              <th style={thStyle}>#</th>
              <th style={thStyle}>Nombre</th>
              <th style={thStyle}>Fecha</th>
              <th style={thStyle}>Hora</th>
            </tr>
          </thead>
          <tbody>
            {records.map((r, i) => {
              const ts = r.timestamp ?? '';
              const datePart = ts.slice(0, 10);
              const timePart = ts.slice(11, 19);
              return (
                <tr key={r.id} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td style={tdStyle}>{(page - 1) * 10 + i + 1}</td>
                  <td style={tdStyle}>{r.name}</td>
                  <td style={tdStyle}>{datePart}</td>
                  <td style={tdStyle}>{timePart}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}

      {!loading && records.length > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 16, marginTop: 20 }}>
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
            style={{
              padding: '6px 14px',
              borderRadius: 6,
              border: '1px solid var(--border)',
              background: page <= 1 ? 'transparent' : 'var(--bg)',
              color: page <= 1 ? 'var(--border)' : 'var(--text-h)',
              fontSize: 14,
              cursor: page <= 1 ? 'not-allowed' : 'pointer',
            }}
          >
            Anterior
          </button>
          <span style={{ fontSize: 14, color: 'var(--text)' }}>
            Pagina {page} de {totalPages}
          </span>
          <button
            type="button"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
            style={{
              padding: '6px 14px',
              borderRadius: 6,
              border: '1px solid var(--border)',
              background: page >= totalPages ? 'transparent' : 'var(--bg)',
              color: page >= totalPages ? 'var(--border)' : 'var(--text-h)',
              fontSize: 14,
              cursor: page >= totalPages ? 'not-allowed' : 'pointer',
            }}
          >
            Siguiente
          </button>
        </div>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

const thStyle: React.CSSProperties = {
  textAlign: 'left',
  padding: '10px 12px',
  color: 'var(--text-h)',
  fontWeight: 600,
  fontSize: 13,
};

const tdStyle: React.CSSProperties = {
  padding: '10px 12px',
  color: 'var(--text)',
};
