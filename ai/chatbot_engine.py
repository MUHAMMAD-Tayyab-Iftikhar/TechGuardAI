class ChatbotEngine:
    def __init__(self, monitor):
        self.monitor = monitor

    def get_response(self, user_input):
        user_input = user_input.lower()
        
        # --- 1. Fetch Real Data ---
        cpu = self.monitor.get_cpu_metrics()
        ram = self.monitor.get_memory_metrics()
        
        # --- 2. Advanced Logic ---
        
        # QUESTION: "Who is slowing me down?" / "Top app"
        if any(w in user_input for w in ["who", "which", "hogging", "heavy", "app"]):
            if "cpu" in user_input:
                top_cpu = self.monitor.get_top_cpu_process()
                return f"The app using the most processing power right now is: {top_cpu}."
            else:
                top_mem = self.monitor.get_heaviest_process()
                return f"The heaviest app in memory is: {top_mem}. Closing it may speed up your PC."

        # QUESTION: "Battery status"
        if "battery" in user_input or "power" in user_input:
            bat = self.monitor.get_battery_report()
            return f"Current Power Status: {bat}. (If on desktop, this may just say AC Power)."

        # QUESTION: "Uptime" / "How long running"
        if "uptime" in user_input or "how long" in user_input:
            uptime = self.monitor.get_system_uptime()
            if "d" in uptime: # If days are involved
                return f"Your system has been running for {uptime}. You should probably restart soon to clear the cache!"
            return f"System Uptime: {uptime}. You are good to go."

        # QUESTION: "Slowness" (Updated Logic)
        if "slow" in user_input or "lag" in user_input:
            if ram['percent'] > 85:
                top_mem = self.monitor.get_heaviest_process()
                return f"Memory is critical ({ram['percent']}%). The main culprit is {top_mem}."
            elif cpu['usage'] > 80:
                top_cpu = self.monitor.get_top_cpu_process()
                return f"High CPU usage ({cpu['usage']}%). {top_cpu} is working very hard."
            else:
                return "Hardware usage is low. The lag might be due to disk fragmentation or internet issues."

        # QUESTION: "Temperature" (Standard)
        if "temperature" in user_input or "hot" in user_input:
            return "I cannot read BIOS sensors directly yet. If your fan is loud, check the 'Top CPU' app—it usually causes the heat."

        # QUESTION: Greetings
        if "hello" in user_input or "hi" in user_input:
            return "Hello! I am connected to your System Monitor. Ask me: 'Who is hogging memory?' or 'Check battery'."

        # Fallback
        return "I can analyze: CPU, Memory, Battery, Uptime, and Top Apps. Try asking 'What is using my RAM?'"