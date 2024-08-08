function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const content = document.getElementById('content');
    const sidebarToggle = document.getElementById('sidebar-toggle');
    
    if (sidebar.classList.contains('hidden')) {
        // Show the sidebar and adjust content
        sidebar.classList.remove('hidden');
        sidebar.classList.add('visible');
        content.classList.remove('expanded');
        content.classList.add('compressed');
        sidebarToggle.style.display = 'none'; // Hide the toggle button
    } else {
        // Hide the sidebar and adjust content
        sidebar.classList.remove('visible');
        sidebar.classList.add('hidden');
        content.classList.remove('compressed');
        content.classList.add('expanded');
        sidebarToggle.style.display = 'block'; // Show the toggle button
    }
}