import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Typography, Collapse, IconButton, Box } from '@mui/material';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';

interface Agent {
    id: number;
    [key: string]: any;
}

const AgentsPage: React.FC = () => {
    const [agents, setAgents] = useState<Agent[]>([]);
    const [columns, setColumns] = useState<string[]>([]);
    const [openRows, setOpenRows] = useState<{ [id: number]: boolean }>({});
    const [tools, setTools] = useState<{ [id: number]: any[] }>({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        axios.get('/agents/')
            .then(res => {
                setAgents(res.data);
                if (res.data.length > 0) {
                    setColumns(Object.keys(res.data[0]));
                }
                setLoading(false);
            })
            .catch(err => {
                setError('Failed to fetch agents');
                setLoading(false);
            });
    }, []);

    const handleRowClick = (id: number) => {
        setOpenRows(prev => ({ ...prev, [id]: !prev[id] }));
        if (!tools[id]) {
            axios.get(`/agents/${id}/tools`).then(res => {
                setTools(prev => ({ ...prev, [id]: res.data }));
            });
        }
    };

    if (loading) return <Typography>Loading...</Typography>;
    if (error) return <Typography color="error">{error}</Typography>;

    return (
        <TableContainer component={Paper} sx={{ mt: 2 }}>
            <Table size="small">
                <TableHead>
                    <TableRow>
                        <TableCell />
                        {columns.map(col => <TableCell key={col}>{col}</TableCell>)}
                    </TableRow>
                </TableHead>
                <TableBody>
                    {agents.map((agent) => (
                        <React.Fragment key={agent.id}>
                            <TableRow>
                                <TableCell>
                                    <IconButton size="small" onClick={() => handleRowClick(agent.id)}>
                                        {openRows[agent.id] ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
                                    </IconButton>
                                </TableCell>
                                {columns.map(col => <TableCell key={col}>{agent[col]}</TableCell>)}
                            </TableRow>
                            <TableRow>
                                <TableCell colSpan={columns.length + 1} sx={{ p: 0, border: 0 }}>
                                    <Collapse in={openRows[agent.id]} timeout="auto" unmountOnExit>
                                        <Box sx={{ m: 2 }}>
                                            <Typography variant="subtitle1">Tools</Typography>
                                            <Table size="small">
                                                <TableHead>
                                                    <TableRow>
                                                        <TableCell>Name</TableCell>
                                                        <TableCell>Description</TableCell>
                                                    </TableRow>
                                                </TableHead>
                                                <TableBody>
                                                    {(tools[agent.id] || []).map((tool: any, idx: number) => (
                                                        <TableRow key={idx}>
                                                            <TableCell>{tool.name}</TableCell>
                                                            <TableCell>{tool.description}</TableCell>
                                                        </TableRow>
                                                    ))}
                                                </TableBody>
                                            </Table>
                                        </Box>
                                    </Collapse>
                                </TableCell>
                            </TableRow>
                        </React.Fragment>
                    ))}
                </TableBody>
            </Table>
        </TableContainer>
    );
};

export default AgentsPage; 