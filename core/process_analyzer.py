import psutil

class ProcessAnalyzer:
    def get_top_processes(self, sort_by='memory', limit=5):
        """
        Returns a list of top resource-consuming processes.
        sort_by: 'memory' or 'cpu'
        """
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent']):
            try:
                # Get process info safely
                p_info = proc.info
                if sort_by == 'memory':
                    # Convert bytes to MB
                    usage = p_info['memory_info'].rss / (1024 * 1024)
                else:
                    usage = p_info['cpu_percent']
                
                processes.append({
                    "pid": p_info['pid'],
                    "name": p_info['name'],
                    "usage": usage
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        # Sort descending
        sorted_procs = sorted(processes, key=lambda x: x['usage'], reverse=True)
        return sorted_procs[:limit]