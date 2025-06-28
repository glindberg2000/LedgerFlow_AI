import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Typography, Button, Box } from '@mui/material';

const UploadsPage: React.FC = () => {
  const [rows, setRows] = useState<any[]>([]);
  const [columns, setColumns] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    axios.get('/uploads/')
      .then(res => {
        setRows(res.data);
        if (res.data.length > 0) {
          setColumns(Object.keys(res.data[0]));
        }
        setLoading(false);
      })
      .catch(err => {
        setError('Failed to fetch uploads');
        setLoading(false);
      });
  }, []);

  const handleBatchUpload = () => {
    alert('Batch upload feature coming soon!');
  };

  if (loading) return <Typography>Loading...</Typography>;
  if (error) return <Typography color="error">{error}</Typography>;

  return (
    <Box sx={{ mt: 2 }}>
      <Button variant="contained" color="primary" onClick={handleBatchUpload} sx={{ mb: 2 }}>
        Batch Upload
      </Button>
      <TableContainer component={Paper}>
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
    </Box>
  );
};

export default UploadsPage; 