import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import AppBar from '@mui/material/AppBar';
import Box from '@mui/material/Box';
import CssBaseline from '@mui/material/CssBaseline';
import Drawer from '@mui/material/Drawer';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import DashboardIcon from '@mui/icons-material/Dashboard';
import PeopleIcon from '@mui/icons-material/People';
import ReceiptIcon from '@mui/icons-material/Receipt';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import BuildIcon from '@mui/icons-material/Build';
import ExtensionIcon from '@mui/icons-material/Extension';
import ListAltIcon from '@mui/icons-material/ListAlt';

const drawerWidth = 220;

const navItems = [
    { text: 'Dashboard', path: '/', icon: <DashboardIcon /> },
    { text: 'Clients', path: '/clients', icon: <PeopleIcon /> },
    { text: 'Transactions', path: '/transactions', icon: <ReceiptIcon /> },
    { text: 'Agents', path: '/agents', icon: <BuildIcon /> },
    { text: 'Tools', path: '/tools', icon: <ExtensionIcon /> },
    { text: 'Uploads', path: '/uploads', icon: <UploadFileIcon /> },
    { text: 'Parsers', path: '/parsers', icon: <ListAltIcon /> },
];

function Placeholder({ title }: { title: string }) {
    return (
        <Box sx={{ p: 3 }}>
            <Typography variant="h4">{title}</Typography>
            <Typography variant="body1" sx={{ mt: 2 }}>
                This page is under construction.
            </Typography>
        </Box>
    );
}

function App() {
    return (
        <Router>
            <Box sx={{ display: 'flex' }}>
                <CssBaseline />
                <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
                    <Toolbar>
                        <Typography variant="h6" noWrap component="div">
                            LedgerFlow Admin
                        </Typography>
                    </Toolbar>
                </AppBar>
                <Drawer
                    variant="permanent"
                    sx={{
                        width: drawerWidth,
                        flexShrink: 0,
                        [`& .MuiDrawer-paper`]: { width: drawerWidth, boxSizing: 'border-box' },
                    }}
                >
                    <Toolbar />
                    <Box sx={{ overflow: 'auto' }}>
                        <List>
                            {navItems.map((item) => (
                                <ListItem button key={item.text} component={Link} to={item.path}>
                                    <ListItemIcon>{item.icon}</ListItemIcon>
                                    <ListItemText primary={item.text} />
                                </ListItem>
                            ))}
                        </List>
                    </Box>
                </Drawer>
                <Box component="main" sx={{ flexGrow: 1, bgcolor: 'background.default', p: 3 }}>
                    <Toolbar />
                    <Routes>
                        <Route path="/" element={<Placeholder title="Dashboard" />} />
                        <Route path="/clients" element={<Placeholder title="Clients" />} />
                        <Route path="/transactions" element={<Placeholder title="Transactions" />} />
                        <Route path="/agents" element={<Placeholder title="Agents" />} />
                        <Route path="/tools" element={<Placeholder title="Tools" />} />
                        <Route path="/uploads" element={<Placeholder title="Uploads" />} />
                        <Route path="/parsers" element={<Placeholder title="Parsers" />} />
                    </Routes>
                </Box>
            </Box>
        </Router>
    );
}

export default App;
