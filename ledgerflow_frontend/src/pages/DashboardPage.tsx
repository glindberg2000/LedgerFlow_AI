import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Box, Card, CardContent, Typography } from '@mui/material';

interface BatchStatusObj {
    status: string;
    message: string;
}

interface DashboardSummary {
    transaction_count: number;
    client_count: number;
    statement_file_count: number;
    batch_status: BatchStatusObj | string;
}

function isBatchStatusObj(obj: any): obj is BatchStatusObj {
    return obj && typeof obj === 'object' && 'status' in obj && 'message' in obj;
}

const DashboardPage: React.FC = () => {
    const [summary, setSummary] = useState<DashboardSummary | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        axios.get('/dashboard/summary')
            .then(res => {
                setSummary(res.data);
                setLoading(false);
            })
            .catch(err => {
                setError('Failed to fetch dashboard summary');
                setLoading(false);
            });
    }, []);

    if (loading) return <Typography>Loading...</Typography>;
    if (error) return <Typography color="error">{error}</Typography>;
    if (!summary) return null;

    return (
        <Box sx={{ flexGrow: 1, p: 2 }}>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                <Card sx={{ flex: '1 1 200px', minWidth: 200, maxWidth: 300 }}>
                    <CardContent>
                        <Typography variant="h6">Transactions</Typography>
                        <Typography variant="h4">{summary.transaction_count}</Typography>
                    </CardContent>
                </Card>
                <Card sx={{ flex: '1 1 200px', minWidth: 200, maxWidth: 300 }}>
                    <CardContent>
                        <Typography variant="h6">Clients</Typography>
                        <Typography variant="h4">{summary.client_count}</Typography>
                    </CardContent>
                </Card>
                <Card sx={{ flex: '1 1 200px', minWidth: 200, maxWidth: 300 }}>
                    <CardContent>
                        <Typography variant="h6">Statement Files</Typography>
                        <Typography variant="h4">{summary.statement_file_count}</Typography>
                    </CardContent>
                </Card>
                <Card sx={{ flex: '1 1 200px', minWidth: 200, maxWidth: 300 }}>
                    <CardContent>
                        <Typography variant="h6">Batch Status</Typography>
                        <Typography variant="h4">
                            {isBatchStatusObj(summary.batch_status)
                                ? `${summary.batch_status.status}: ${summary.batch_status.message}`
                                : String(summary.batch_status)}
                        </Typography>
                    </CardContent>
                </Card>
            </Box>
        </Box>
    );
};

export default DashboardPage; 