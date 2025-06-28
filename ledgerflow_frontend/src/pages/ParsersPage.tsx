import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Typography } from '@mui/material';

const ParsersPage: React.FC = () => {
    const [parsers, setParsers] = useState<any[]>([]);
    const [columns, setColumns] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        axios.get('/uploads/parsers')
            .then(res => {
                setParsers(res.data);
                if (res.data.length > 0) {
                    setColumns(Object.keys(res.data[0]));
                }
                setLoading(false);
            })
            .catch(err => {
                setError('Failed to fetch parsers');
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
                    {parsers.map((parser, idx) => (
                        <TableRow key={idx}>
                            {columns.map(col => <TableCell key={col}>{parser[col]}</TableCell>)}
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </TableContainer>
    );
};

export default ParsersPage; 