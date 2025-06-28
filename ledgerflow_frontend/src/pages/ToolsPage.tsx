import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Typography } from '@mui/material';

const ToolsPage: React.FC = () => {
    const [rows, setRows] = useState<any[]>([]);
    const [columns, setColumns] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        axios.get('/tools/')
            .then(res => {
                setRows(res.data);
                if (res.data.length > 0) {
                    setColumns(Object.keys(res.data[0]));
                }
                setLoading(false);
            })
            .catch(err => {
                setError('Failed to fetch tools');
                setLoading(false);
            });
    }, []);

    if (loading) return <Typography>Loading...</Typography>;
    if (error) return <Typography color="error">{error}</Typography>;

    return (
        <TableContainer component={Paper} sx={{ mt: 2 }}>
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
    );
};

export default ToolsPage; 