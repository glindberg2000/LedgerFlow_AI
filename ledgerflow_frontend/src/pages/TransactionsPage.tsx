import React, { useEffect, useState, useMemo } from 'react';
import axios from 'axios';
import {
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Typography, TablePagination, TextField, InputAdornment, IconButton, MenuItem, Select, FormControl, InputLabel, Box, CircularProgress, TableSortLabel, Tooltip, Divider
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import dayjs, { Dayjs } from 'dayjs';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';

function debounce<T extends (...args: any[]) => void>(fn: T, delay: number) {
    let timeout: ReturnType<typeof setTimeout>;
    return (...args: Parameters<T>) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => fn(...args), delay);
    };
}

const getYearRange = (start: number, end: number) => {
    const years = [];
    for (let y = end; y >= start; y--) years.push(y);
    return years;
};

const TransactionsPage: React.FC = () => {
    const [rows, setRows] = useState<any[]>([]);
    const [columns, setColumns] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [page, setPage] = useState(0);
    const [rowsPerPage, setRowsPerPage] = useState(25);
    const [total, setTotal] = useState(0);
    const [search, setSearch] = useState('');
    const [searchInput, setSearchInput] = useState('');
    const [sortBy, setSortBy] = useState('transaction_date');
    const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
    const [clientId, setClientId] = useState('');
    const [clients, setClients] = useState<string[]>([]);
    // Date filter state
    const currentYear = new Date().getFullYear();
    const [year, setYear] = useState<number | ''>('');
    const [startDate, setStartDate] = useState<Dayjs | null>(null);
    const [endDate, setEndDate] = useState<Dayjs | null>(null);
    const yearRange = useMemo(() => getYearRange(currentYear - 10, currentYear + 1), [currentYear]);

    // Define which columns to show by default (summary view)
    const summaryColumns = [
        'transaction_date',
        'amount',
        'payee',
        'payee_reasoning',
        'normalized_description',
        'transaction_type',
        'classification_type',
        'confidence',
        'worksheet',
        'reasoning',
        'questions',
        'parsed_data',
        'category', 'source', 'parser_name', 'description', 'account_number', 'client_id', 'transaction_id', 'normalized_amount', 'file_path',
    ];
    const allColumns = [
        'transaction_date',
        'amount',
        'payee',
        'payee_reasoning',
        'normalized_description',
        'transaction_type',
        'classification_type',
        'confidence',
        'worksheet',
        'reasoning',
        'questions',
        'parsed_data',
        'category', 'source', 'parser_name', 'description', 'account_number', 'client_id', 'transaction_id', 'normalized_amount', 'file_path',
        'business_context', 'statement_start_date', 'statement_end_date', 'needs_account_number', 'transaction_hash'
    ];
    const truncatedColumns = [
        'description', 'reasoning', 'business_context', 'questions', 'payee_reasoning', 'normalized_description', 'file_path', 'parser_name', 'category', 'source', 'payee'
    ];
    const iconTooltipColumns = ['reasoning', 'business_context', 'questions', 'payee_reasoning', 'parsed_data'];
    const TRUNCATE_LENGTH = 40;

    const [showAllColumns, setShowAllColumns] = useState(false);
    const [availableYears, setAvailableYears] = useState<number[]>([]);

    // Fetch clients for filter dropdown
    useEffect(() => {
        axios.get('/business-profiles/')
            .then(res => {
                const items = res.data.items || res.data.results || res.data || [];
                setClients(items.map((c: any) => c.client_id));
            })
            .catch(() => setClients([]));
    }, []);

    // Debounced search effect
    useEffect(() => {
        const handler = setTimeout(() => {
            setSearch(searchInput);
            setPage(0); // Reset to first page on new search
        }, 300);
        return () => clearTimeout(handler);
    }, [searchInput]);

    // Fetch transactions
    useEffect(() => {
        setLoading(true);
        setError(null);
        axios.get('/transactions/', {
            params: {
                offset: page * rowsPerPage,
                limit: rowsPerPage,
                client_id: clientId || undefined,
                search: search || undefined,
                sort: sortDir,
                sort_by: sortBy,
                year: year || undefined,
                start_date: startDate ? startDate.format('YYYY-MM-DD') : undefined,
                end_date: endDate ? endDate.format('YYYY-MM-DD') : undefined,
            }
        })
            .then(res => {
                const items = res.data.items || res.data.results || res.data || [];
                setRows(Array.isArray(items) ? items : []);
                setTotal(res.data.total || res.data.length || 0);
                if (Array.isArray(items) && items.length > 0) {
                    setColumns(Object.keys(items[0]));
                }
                setLoading(false);
            })
            .catch(err => {
                setError('Failed to fetch transactions');
                setLoading(false);
            });
    }, [page, rowsPerPage, clientId, search, sortBy, sortDir, year, startDate, endDate]);

    // Fetch available years for the selected client (short-term: fetch all transactions for client)
    useEffect(() => {
        if (!clientId) {
            setAvailableYears([]);
            return;
        }
        axios.get('/transactions/', {
            params: {
                client_id: clientId,
                page: 1,
                page_size: 10000, // Large limit for year scan
            }
        }).then(res => {
            const items = res.data.items || res.data.results || res.data || [];
            const years = new Set<number>();
            items.forEach((row: any) => {
                if (row.transaction_date) {
                    const y = new Date(row.transaction_date).getFullYear();
                    if (!isNaN(y)) years.add(y);
                }
            });
            setAvailableYears(Array.from(years).sort((a, b) => b - a));
        }).catch(() => setAvailableYears([]));
    }, [clientId]);

    const handleChangePage = (event: unknown, newPage: number) => {
        setPage(newPage);
    };

    const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
        setRowsPerPage(parseInt(event.target.value, 10));
        setPage(0);
    };

    const handleSearchInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setSearchInput(e.target.value);
    };

    const handleClientChange = (e: any) => {
        setClientId(e.target.value);
        setPage(0);
    };

    // Sorting handler for column headers
    const handleSort = (col: string) => {
        if (sortBy === col) {
            setSortDir(prev => (prev === 'asc' ? 'desc' : 'asc'));
        } else {
            setSortBy(col);
            setSortDir('asc');
        }
        setPage(0);
    };

    // Date filter handlers
    const handleYearChange = (e: any) => {
        setYear(e.target.value);
        setStartDate(null);
        setEndDate(null);
        setPage(0);
    };
    const handleStartDateChange = (date: Dayjs | null) => {
        setStartDate(date);
        setYear('');
        setPage(0);
    };
    const handleEndDateChange = (date: Dayjs | null) => {
        setEndDate(date);
        setYear('');
        setPage(0);
    };

    // Columns to allow sorting on (add more as needed)
    const sortableColumns = useMemo(() => [
        'transaction_date', 'amount', 'category', 'source', 'payee', 'parser_name', 'description', 'account_number', 'client_id'
    ], []);

    const visibleColumns = showAllColumns ? allColumns.filter(col => columns.includes(col)) : summaryColumns.filter(col => columns.includes(col));

    if (loading) return <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px"><CircularProgress /></Box>;
    if (error) return <Typography color="error">{error}</Typography>;

    return (
        <Paper sx={{ mt: 2, p: 2 }}>
            <Box display="flex" gap={2} mb={2} alignItems="center" flexWrap="wrap">
                <FormControl sx={{ minWidth: 200, mb: 1 }}>
                    <InputLabel id="client-select-label">Client</InputLabel>
                    <Select
                        labelId="client-select-label"
                        value={clientId}
                        label="Client"
                        onChange={handleClientChange}
                    >
                        <MenuItem value=""><em>Select Client</em></MenuItem>
                        {clients.map(cid => (
                            <MenuItem key={cid} value={cid}>{cid}</MenuItem>
                        ))}
                    </Select>
                </FormControl>
                <TextField
                    label="Search Description/Payee"
                    value={searchInput}
                    onChange={handleSearchInputChange}
                    InputProps={{
                        endAdornment: (
                            <InputAdornment position="end">
                                <IconButton>
                                    <SearchIcon />
                                </IconButton>
                            </InputAdornment>
                        )
                    }}
                    sx={{ minWidth: 300, mb: 1 }}
                />
                <FormControl sx={{ minWidth: 120, mb: 1 }}>
                    <InputLabel id="year-select-label">Year</InputLabel>
                    <Select
                        labelId="year-select-label"
                        value={year}
                        label="Year"
                        onChange={handleYearChange}
                    >
                        <MenuItem value=""><em>All Years</em></MenuItem>
                        {availableYears.map(y => (
                            <MenuItem key={y} value={y}>{y}</MenuItem>
                        ))}
                    </Select>
                </FormControl>
                <DatePicker
                    label="Start Date"
                    value={startDate}
                    onChange={handleStartDateChange}
                    slotProps={{ textField: { sx: { minWidth: 140, mb: 1 } } }}
                    maxDate={endDate || undefined}
                />
                <DatePicker
                    label="End Date"
                    value={endDate}
                    onChange={handleEndDateChange}
                    slotProps={{ textField: { sx: { minWidth: 140, mb: 1 } } }}
                    minDate={startDate || undefined}
                />
            </Box>
            <Box display="flex" alignItems="center" justifyContent="space-between" mb={1}>
                <Typography variant="subtitle2">
                    Showing {rows.length} of {total} transactions
                    {clientId && ` for client ${clientId}`}
                    {year && ` in year ${year}`}
                    {(startDate || endDate) && ` in date range${startDate ? ` from ${startDate.format('YYYY-MM-DD')}` : ''}${endDate ? ` to ${endDate.format('YYYY-MM-DD')}` : ''}`}
                </Typography>
                <Box>
                    <IconButton onClick={() => setShowAllColumns(v => !v)} size="small">
                        {showAllColumns ? 'Summary view' : 'Show all columns'}
                    </IconButton>
                </Box>
            </Box>
            <Divider sx={{ mb: 1 }} />
            <TableContainer>
                <TablePagination
                    component="div"
                    count={total}
                    page={page}
                    onPageChange={handleChangePage}
                    rowsPerPage={rowsPerPage}
                    onRowsPerPageChange={handleChangeRowsPerPage}
                    rowsPerPageOptions={[10, 25, 50, 100]}
                    sx={{ borderBottom: 1, borderColor: 'divider', background: '#fafafa' }}
                />
                <Table size="small">
                    <TableHead>
                        <TableRow sx={{ backgroundColor: theme => theme.palette.grey[200] }}>
                            {visibleColumns.map(col => (
                                <TableCell
                                    key={col}
                                    sortDirection={sortBy === col ? sortDir : false}
                                    sx={{
                                        maxWidth: 180,
                                        whiteSpace: 'nowrap',
                                        overflow: 'hidden',
                                        textOverflow: 'ellipsis',
                                        fontWeight: 'bold',
                                        fontSize: '1rem',
                                        textTransform: 'uppercase',
                                        letterSpacing: 0.5,
                                    }}
                                >
                                    {sortableColumns.includes(col) ? (
                                        <TableSortLabel
                                            active={sortBy === col}
                                            direction={sortBy === col ? sortDir : 'asc'}
                                            onClick={() => handleSort(col)}
                                        >
                                            {col}
                                        </TableSortLabel>
                                    ) : (
                                        col
                                    )}
                                </TableCell>
                            ))}
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {rows.map((row, idx) => (
                            <TableRow key={idx}>
                                {visibleColumns.map(col => {
                                    const value = row[col];
                                    const isTruncated = truncatedColumns.includes(col) && typeof value === 'string' && value.length > TRUNCATE_LENGTH;
                                    const isIconTooltip = iconTooltipColumns.includes(col) && typeof value === 'string' && value.length > 0;
                                    return (
                                        <TableCell key={col} sx={{ maxWidth: 180, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                            {isIconTooltip ? (
                                                <Tooltip title={value} arrow>
                                                    <IconButton size="small"><InfoOutlinedIcon fontSize="small" /></IconButton>
                                                </Tooltip>
                                            ) : isTruncated ? (
                                                <Tooltip title={value} arrow>
                                                    <span>{value.slice(0, TRUNCATE_LENGTH)}&hellip;</span>
                                                </Tooltip>
                                            ) : (
                                                typeof value === 'object' && value !== null
                                                    ? JSON.stringify(value)
                                                    : value
                                            )}
                                        </TableCell>
                                    );
                                })}
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
                <TablePagination
                    component="div"
                    count={total}
                    page={page}
                    onPageChange={handleChangePage}
                    rowsPerPage={rowsPerPage}
                    onRowsPerPageChange={handleChangeRowsPerPage}
                    rowsPerPageOptions={[10, 25, 50, 100]}
                    sx={{ borderTop: 1, borderColor: 'divider', background: '#fafafa' }}
                />
            </TableContainer>
        </Paper>
    );
};

export default TransactionsPage; 