// EDIT TEST: This comment was added by the AI to verify file editing.
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import AppBar from '@mui/material/AppBar';
import Box from '@mui/material/Box';
import CssBaseline from '@mui/material/CssBaseline';
import Drawer from '@mui/material/Drawer';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
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
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';

import DashboardPage from './pages/DashboardPage';
import ClientsPage from './pages/ClientsPage';
import TransactionsPage from './pages/TransactionsPage';
import AgentsPage from './pages/AgentsPage';
import ToolsPage from './pages/ToolsPage';
import UploadsPage from './pages/UploadsPage';
import ParsersPage from './pages/ParsersPage';

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

function App() {
    return (
        <LocalizationProvider dateAdapter={AdapterDayjs}>
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
                                    <ListItem key={item.text} disablePadding>
                                        <ListItemButton component={Link} to={item.path}>
                                            <ListItemIcon>{item.icon}</ListItemIcon>
                                            <ListItemText primary={item.text} />
                                        </ListItemButton>
                                    </ListItem>
                                ))}
                            </List>
                        </Box>
                    </Drawer>
                    <Box component="main" sx={{ flexGrow: 1, bgcolor: 'background.default', p: 3 }}>
                        <Toolbar />
                        <Routes>
                            <Route path="/" element={<DashboardPage />} />
                            <Route path="/clients" element={<ClientsPage />} />
                            <Route path="/transactions" element={<TransactionsPage />} />
                            <Route path="/agents" element={<AgentsPage />} />
                            <Route path="/tools" element={<ToolsPage />} />
                            <Route path="/uploads" element={<UploadsPage />} />
                            <Route path="/parsers" element={<ParsersPage />} />
                        </Routes>
                    </Box>
                </Box>
            </Router>
        </LocalizationProvider>
    );
}

export default App;
