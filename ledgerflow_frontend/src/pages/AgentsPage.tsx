import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Typography, Tooltip } from '@mui/material';

interface Agent {
    id: number;
    name: string;
    purpose: string;
    prompt: string;
    llm_name?: string;
    tools?: string[];
}

const MAX_PROMPT_LENGTH = 40;

const AgentsPage: React.FC = () => {
    const [agents, setAgents] = useState<Agent[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        axios.get('/agents/')
            .then(res => {
                setAgents(res.data);
                setLoading(false);
            })
            .catch(err => {
                setError('Failed to fetch agents');
                setLoading(false);
            });
    }, []);

    if (loading) return <Typography>Loading...</Typography>;
    if (error) return <Typography color="error">{error}</Typography>;

    return (
        <TableContainer component={Paper} sx={{ mt: 2, maxWidth: 1200, mx: 'auto' }}>
            <Table size="small">
                <TableHead>
                    <TableRow>
                        <TableCell><b>Name</b></TableCell>
                        <TableCell><b>Purpose</b></TableCell>
                        <TableCell><b>Prompt</b></TableCell>
                        <TableCell><b>LLM</b></TableCell>
                        <TableCell><b>Tools</b></TableCell>
                    </TableRow>
                </TableHead>
                <TableBody>
                    {agents.map((agent) => (
                        <TableRow key={agent.id}>
                            <TableCell>{agent.name}</TableCell>
                            <TableCell>{agent.purpose}</TableCell>
                            <TableCell>
                                <Tooltip title={agent.prompt || ''} placement="top" arrow>
                                    <span>
                                        {agent.prompt && agent.prompt.length > MAX_PROMPT_LENGTH
                                            ? agent.prompt.slice(0, MAX_PROMPT_LENGTH) + '...'
                                            : agent.prompt}
                                    </span>
                                </Tooltip>
                            </TableCell>
                            <TableCell>{agent.llm_name || '-'}</TableCell>
                            <TableCell>{agent.tools && agent.tools.length > 0 ? agent.tools.join(', ') : '-'}</TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </TableContainer>
    );
};

export default AgentsPage; 