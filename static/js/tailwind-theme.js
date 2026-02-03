tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        nesta: {
                            blue: '#0000FF',        
                            navy: '#0F294A',        
                            pink: '#F6A4B7',        
                            yellow: '#FDB633',      
                            green: '#18A48C',       
                            aqua: '#97D9E3',        
                            purple: '#9A1BBE',      
                            orange: '#FF6E47',      
                            red: '#EB003B',         
                            sand: '#D2C9C0',        
                            darkgrey: '#646363',    
                            black: '#000000',       
                            white: '#FFFFFF'        
                        }
                    },
                    fontFamily: {
                        display: ['"Zosia Display"', 'sans-serif'],
                        body: ['"Averta"', 'sans-serif']
                    },
                    animation: {
                        'fade-in-up': 'fadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards',
                        'radar-spin': 'spin 2s linear infinite',
                        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                        'pop': 'pop 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)',
                    },
                    keyframes: {
                        fadeInUp: {
                            '0%': { opacity: '0', transform: 'translateY(15px)' },
                            '100%': { opacity: '1', transform: 'translateY(0)' }
                        },
                        pop: {
                            '0%': { transform: 'scale(0.95)' },
                            '100%': { transform: 'scale(1)' }
                        },
                        pulse: {
                            '0%, 100%': { opacity: '1' },
                            '50%': { opacity: '0.6' }
                        }
                    },
                    boxShadow: {
                        'soft': '0 4px 20px -2px rgba(15, 41, 74, 0.08)',
                        'hover': '0 10px 30px -5px rgba(0, 0, 255, 0.15)',
                        'glow': '0 0 15px rgba(151, 217, 227, 0.3)',
                    }
                }
            }
        }
