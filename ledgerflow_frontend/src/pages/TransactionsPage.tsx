import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Typography, TablePagination } from '@mui/material';

const TransactionsPage: React.FC = () => {
    const [rows, setRows] = useState<any[]>([]);
    const [columns, setColumns] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [page, setPage] = useState(0);
    const [rowsPerPage, setRowsPerPage] = useState(25);
    const [total, setTotal] = useState(0);

    useEffect(() => {
        setLoading(true);
        axios.get('/transactions/', { params: { page: page + 1, page_size: rowsPerPage } })
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
    }, [page, rowsPerPage]);

    const handleChangePage = (event: unknown, newPage: number) => {
        setPage(newPage);
    };

    const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
        setRowsPerPage(parseInt(event.target.value, 10));
        setPage(0);
    };

    if (loading) return <Typography>Loading...</Typography>;
    if (error) return <Typography color="error">{error}</Typography>;

    return (
        <Paper sx={{ mt: 2 }}>
            <TableContainer>
                <Table size="small">
                    <TableHead>
                        <TableRow>
                            {columns.map(col => <TableCell key={col}>{col}</TableCell>)}
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {rows.map((row, idx) => (
                            <TableRow key={idx}>
                                {columns.map(col => <TableCell key={col}>{row[col]}</TableCell>)}
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>
            <TablePagination
                component="div"
                count={total}
                page={page}
                onPageChange={handleChangePage}
                rowsPerPage={rowsPerPage}
                onRowsPerPageChange={handleChangeRowsPerPage}
                rowsPerPageOptions={[10, 25, 50, 100]}
            />
        </Paper>
    );
};

export default TransactionsPage; 