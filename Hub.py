# Connor Wilson
# Winter 2022
# SMSS Hub Controller V1.0


from smbus2 import SMBus, i2c_msg        # I2C library
from time import sleep                   # python delay

from transitions import Machine          # state machine

import curses                            # GUI
from curses import wrapper
from curses.textpad import Textbox, rectangle



class HubMachine(object):

    states = ['START', 'DATAPULL', 'RUN', 'RESET']   

    def __init__(self,name):
        self.name = name

        # States and their corresponding triggers/transitions
        self.machine = Machine(model= self, states = HubMachine.states, initial = 'START')
        self.machine.add_transition(trigger = 'CONFIRM', source = 'START', dest = 'DATAPULL')
        self.machine.add_transition(trigger = 'EVENTSTART', source = 'DATAPULL', dest = 'RUN')
        self.machine.add_transition(trigger = 'DONE', source = 'RUN', dest = 'RESET')
        self.machine.add_transition(trigger = 'RETURN', source = 'RESET', dest = 'START')
        self.machine.add_transition(trigger = 'REBOOT', source = '*', dest = 'RESET')

# States for GUI
global FRAME, POLL, DATA, RUN
global reqGUI
reqGUI = 0x0
FRAME = 0x0
POLL = 0x1
DATA = 0x2
RUN = 0x3


# Data between user-curses-arduino
global rollcall, poll_user, q_user, radius_user, cap_user
global hour_user, min_user, sec_user, dir_user
rollcall = [0, 0, 0]
poll_user = [0, 0, 0]
q_user = [0,0,0]
radius_user = [0,0,0]
cap_user = [0,0,0]
hour_user = [0,0,0]
min_user = [0,0,0]
sec_user = [0,0,0]
dir_user = [0,0,0]                                              # 0 - REV, 1 - FWD 

    
def main():
    
    # I2C Addresses
    PI_ADD = 0x01                       
    ARD_ADD_1 = 0x14
    ARD_ADD_2 = 0x28
    ARD_ADD_3 = 0x42
    address = [ARD_ADD_1, ARD_ADD_2, ARD_ADD_3]

    # Pi's Dictating (main) codes 
    POLLDATA =  1                       # Ard will recv[OFF, JOG, START] 
    Q_DATA  = 2                         # Ard will recv[q_user]
    R_DATA  = 3                         # Ard will recv[syr_radius_user]
    CAP_DATA = 4                        # Ard will recv[syr_capacity]
    DUR_DATA = 5                        # Ard will recv[hour_user, min_user, sec_user]
    DIR_DATA = 6                        # Ard will recv[DIRECTION]
    EVENT_DATA = 7                      # Ard will recv[true - proceed to RUN from DATAPULL]
    ESTOP_DATA = 8                      # Ard will recv[true - ESTOP condition]

    # Arduino's Requested (Sub) codes                       
    LARGE_ERR = 0x3                     # User req too large (Q) for hardware constraints
    SMALL_ERR = 0x4                     # User req too small (Q) for hardware constraints
    DUR_ERR = 0x5                       # User req too long (time) for hardware constraints
    LD_ERR = 0x6                        # User too large and long
    SD_ERR = 0x7                        # User too small and long
    DICT_ERR = 0x8                      # Wrong dictating codes
    NO_ERR = 0x10                       # No error to report

    WAIT_CODE = 0x15                    # Ard needs time to pull data and validate 
    FINISH_CODE=  0x16                  # Ard's duration has been reached and finished RUN_S
    TIME_CODE =  0x17                   # Ard is not done with RUN_S and will return time(h,m,s) if prompted
    
    #availability of arduino deivces 0 = false, 1 = true
    global rollcall
    rollcall = [0,0,0]

    # GUI command codes
    global FRAME, POLL, DATA, RUN
    global reqGUI

    #curses window
    stdscr = curses.initscr()
    
    #state machine init
    Hub = HubMachine("SMSS")

    while True:

        if Hub.state == 'START' :

            #Identify devices on the buffer
            rollcall = deviceRollcall(address)
            sleep(1)

            #Display GUI background frame
            reqGUI = FRAME
            curs(stdscr)
            
            # Poll user for device run modes
            reqGUI = POLL
            curs(stdscr)

            # Write dictation code + poll_user
            for i in range(3):
                if rollcall[i] > 0:
                    #print(f"{poll_user[i]}")
                    transmit_block(address[i], POLLDATA, poll_user[i] )
                else:
                    #print("Dont got'em")
                    pass
            
            # Change states to DATAPULL
            Hub.CONFIRM()


        elif Hub.state == 'DATAPULL' :
            reqGUI = DATA
            curs(stdscr)

            for i in range(3):
                # if device is on bus
                if rollcall[i] > 0:
                    # if device is in JOG
                    if poll_user[i] == 1:
                        # transmit variables
                        transmit_block(address[i], Q_DATA, int(q_user[i]))
                        transmit_block(address[i], R_DATA, int(radius_user[i]) )
                        transmit_block(address[i], DIR_DATA, int(dir_user[i]) )
                        # ticket request
                        #  if not, them feedback request
                                       
                    # if device is in RUN
                    elif poll_user[i] == 2:
                        print(f"{q_user[i]}");
                        transmit_block(address[i], Q_DATA, int(q_user[i]) )
                        transmit_block(address[i], R_DATA, int(radius_user[i]) )
                        transmit_block(address[i], CAP_DATA, int(cap_user[i]) )
                        transmit_block(address[i], DUR_DATA, int(hour_user[i]) )
                        transmit_block(address[i], DUR_DATA, int(min_user[i]) )
                        transmit_block(address[i], DUR_DATA, int(sec_user[i]) )
                        transmit_block(address[i], DIR_DATA, int(dir_user[i]) )
                        # ticket request
                        #  if not, them feedback request

            # if all present devices have tickets, Hub.EVENTSTART() 

        elif Hub.state == 'RUN' :
            pass

        elif Hub.state == 'RESET' : 
            pass

        elif Hub.state == 'REBOOT' : 
            pass

        else: 
            pass


    

        

# transmit__block()
# SIGNATURE : int, int, int -> 
# PURPOSE : Transmits a dictating code +  data to an address
#           
def transmit_block(addr, dict_code, int_data):
        
    with SMBus(1) as bus:
        bus.write_byte(addr,  dict_code)
        sleep(0.1)
        bus.write_byte(addr,  int_data)
            


# recv_all_byte()
# SIGNATURE : bool -> int
# PURPOSE : Reads identical byte of data from all enabled arduinos
#           and Returns array of resulting byte
def recv_all_byte(bool_array):

    stor = [0,0,0]
        
    with SMBus(1) as bus: # write to BUS

        # device one is requested active -> write
        if bool_array[0] > 0 :
            stor[0] = bus.read_byte(ARD_ADD_1, 0)

        # device two is requested active -> write
        if bool_array[1] > 0 :
            stor[1] = bus.read_byte(ARD_ADD_2, 0)

        # device three is requested active -> write
        if bool_array[2] > 0 :
            stor[2] = bus.read_byte(ARD_ADD_3, 0)

        return stor
        

# deviceRollcall()
# SIGNATURE : int_array -> int_array
# Purpose : Sends byte to each device using I2C and 
#           Stores 1 in array for a sucessful transmission (device active)
#           Stores 0 in array for unsuccessful transmission (device not active)
def deviceRollcall(myaddress):

    dev_status = [0, 0, 0]

    with SMBus(1) as bus: # write to BUS

        for i in range(3):

            # Try to contact each device
            try:
                bus.write_byte(myaddress[i], 0)
                dev_status[i] = 1
                print(f"Device {i} on bus")
            except:
                #print(f"Device {i} not on bus")
                dev_status[i] = 0
                pass
        
    return dev_status

 

def curs(stdscr):

    global FRAME, POLL, DATA, RUN
    global reqGUI
    global rollcall, poll_user, q_user, radius_user, cap_user
    global hour_user, min_user, sec_user, dir_user
    
    # Color combinations (ID, foreground, background)
    curses.init_pair(1, curses.COLOR_RED, curses.COLOR_WHITE)
    RED_AND_WHITE = curses.color_pair(1)

    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
    BLACK_AND_WHITE = curses.color_pair(2)

    curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_GREEN)
    WHITE_AND_GREEN = curses.color_pair(3)

    curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_CYAN)
    YELLOW_AND_CYAN = curses.color_pair(4)

    curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_MAGENTA)
    WHITE_AND_MAGENTA = curses.color_pair(5)
    

    # Display background frame
    if reqGUI == FRAME:
        stdscr.clear()
        stdscr.attron(YELLOW_AND_CYAN)
        stdscr.resize(28,100)
        stdscr.move(0,0)

        # Fill square main in 
        for y in range(1,28):
            for x in range(1, 100-1):
                stdscr.addch(" ")
            stdscr.move(y,1)
        stdscr.border()

        #Title block
        stdscr.move(2,30)
        stdscr.addstr("        Smart Motor Syringe Pump        ", BLACK_AND_WHITE)


        
        stdscr.attroff(YELLOW_AND_CYAN)
        stdscr.attron(BLACK_AND_WHITE)

        #Device one block
        stdscr.move(5,10)
        stdscr.addstr("Device 1 :")
        stdscr.move(5,30)

        for y in range(5,11):
            for x in range(30, 90-1):
                stdscr.addch(" ")
            stdscr.move(y,30)

        # Device two block
        stdscr.move(12,10)
        stdscr.addstr("Device 2 :")
        stdscr.move(12,30)

        for y in range(12,18):
            for x in range(30, 90-1):
                stdscr.addch(" ")
            stdscr.move(y,30)

        # Device three block
        stdscr.move(19,10)
        stdscr.addstr("Device 3 :")
        stdscr.move(19,30)

        for y in range(19,25):
            for x in range(30, 90-1):
                stdscr.addch(" ")
            stdscr.move(y,30)


        #Re-center and refresh
        stdscr.move(21,40)
        stdscr.addstr(25, 35, "                                             ")
        stdscr.move(5,30)
        stdscr.refresh()

        
    # Poll user for device run modes
    elif reqGUI == POLL:

        if rollcall[0] > 0:
            # display window
            winPoll1 = curses.newwin(5, 60, 5, 30)
            curses.noecho()
            winPoll1.nodelay(True)
            winPoll1.clear()
            winPoll1.attron(WHITE_AND_GREEN)
            winPoll1.addstr(1, 5, "Device 1 Mode :      | OFF | JOG | RUN |")
            winPoll1.addstr(3, 5, "Error Messages : ")
            winPoll1.refresh()
            
            # collect data
            q = 0
            key = ""

            while key != 'w':

                winPoll1.attroff(BLACK_AND_WHITE)     
                winPoll1.attron(WHITE_AND_GREEN)
                winPoll1.addstr(1, 5, "Device 1 Mode :      | OFF | JOG | RUN |")

                try:
                    key = winPoll1.getkey()
                except:
                    key = None

                if key == 'a':
                    if q > 0:
                        q -= 1
                        
                elif key == 'd':
                    if q < 2:
                        q += 1


                if q == 0:
                    winPoll1.attroff(WHITE_AND_GREEN)
                    winPoll1.attron(BLACK_AND_WHITE)
                    winPoll1.addstr(1, 26, "| OFF |")
                    poll_user[0] = 0                    # disable the device
                    
                elif q == 1:
                    winPoll1.attroff(WHITE_AND_GREEN)
                    winPoll1.attron(BLACK_AND_WHITE)
                    winPoll1.addstr(1, 32, "| JOG |")
                    poll_user[0] = 1                    # jog the device

                elif q == 2:
                    winPoll1.attroff(WHITE_AND_GREEN)
                    winPoll1.attron(BLACK_AND_WHITE)
                    winPoll1.addstr(1, 38, "| RUN |")
                    poll_user[0] = 2                    # run the device
                        
                
                winPoll1.refresh()
                sleep(0.5)

        if rollcall[1] > 0:
            # display window
            winPoll2 = curses.newwin(5, 60, 12, 30)
            curses.noecho()
            winPoll2.nodelay(True)
            winPoll2.clear()
            winPoll2.attron(WHITE_AND_GREEN)
            winPoll2.addstr(1, 5, "Device 1 Mode :      | OFF | JOG | RUN |")
            winPoll2.addstr(3, 5, "Error Messages : ")
            winPoll2.refresh()
            
            # collect data
            q = 0
            key = ""

            while key != 'w':

                winPoll2.attroff(BLACK_AND_WHITE)     
                winPoll2.attron(WHITE_AND_GREEN)
                winPoll2.addstr(1, 5, "Device 1 Mode :      | OFF | JOG | RUN |")

                try:
                    key = winPoll2.getkey()
                except:
                    key = None

                if key == 'a':
                    if q > 0:
                        q -= 1
                        
                elif key == 'd':
                    if q < 2:
                        q += 1


                if q == 0:
                    winPoll2.attroff(WHITE_AND_GREEN)
                    winPoll2.attron(BLACK_AND_WHITE)
                    winPoll2.addstr(1, 26, "| OFF |")
                    poll_user[1] = 0                    # disable the device
                    
                elif q == 1:
                    winPoll2.attroff(WHITE_AND_GREEN)
                    winPoll2.attron(BLACK_AND_WHITE)
                    winPoll2.addstr(1, 32, "| JOG |")
                    poll_user[1] = 1                    # jog the device

                elif q == 2:
                    winPoll2.attroff(WHITE_AND_GREEN)
                    winPoll2.attron(BLACK_AND_WHITE)
                    winPoll2.addstr(1, 38, "| RUN |")
                    poll_user[1] = 2                    # run the device
                        
                
                winPoll2.refresh()
                sleep(0.5)

        if rollcall[2] > 0:
            # display window
            winPoll3 = curses.newwin(5, 60, 19, 30)
            curses.noecho()
            winPoll3.nodelay(True)
            winPoll3.clear()
            winPoll3.attron(WHITE_AND_GREEN)
            winPoll3.addstr(1, 5, "Device 1 Mode :      | OFF | JOG | RUN |")
            winPoll3.addstr(3, 5, "Error Messages : ")
            winPoll3.refresh()
            
            # collect data
            q = 0
            key = ""

            while key != 'w':

                winPoll3.attroff(BLACK_AND_WHITE)     
                winPoll3.attron(WHITE_AND_GREEN)
                winPoll3.addstr(1, 5, "Device 1 Mode :      | OFF | JOG | RUN |")

                try:
                    key = winPoll3.getkey()
                except:
                    key = None

                if key == 'a':
                    if q > 0:
                        q -= 1
                        
                elif key == 'd':
                    if q < 2:
                        q += 1


                if q == 0:
                    winPoll3.attroff(WHITE_AND_GREEN)
                    winPoll3.attron(BLACK_AND_WHITE)
                    winPoll3.addstr(1, 26, "| OFF |")
                    poll_user[2] = 0                    # disable the device
                    
                elif q == 1:
                    winPoll3.attroff(WHITE_AND_GREEN)
                    winPoll3.attron(BLACK_AND_WHITE)
                    winPoll3.addstr(1, 32, "| JOG |")
                    poll_user[2] = 1                    # jog the device

                elif q == 2:
                    winPoll3.attroff(WHITE_AND_GREEN)
                    winPoll3.attron(BLACK_AND_WHITE)
                    winPoll3.addstr(1, 38, "| RUN |")
                    poll_user[2] = 2                    # run the device
                        
                
                winPoll3.refresh()
                sleep(0.5)

        # display window
        winPoll4 = curses.newwin(1, 46, 25, 35)
        curses.noecho()
        winPoll4.nodelay(True)
        winPoll4.clear()
        winPoll4.attron(WHITE_AND_GREEN)
        winPoll4.addstr(0, 18, "| CONFIRM? |")
        winPoll4.refresh()
            
        key = ""

        while key != 'w':

            try:
                key = winPoll4.getkey()
            except:
                key = None
                
        winPoll4.refresh()
        sleep(0.5)
        
    # Poll metrics for running in START
    elif reqGUI == DATA:

        # Act if device one is on the bus
        if rollcall[0] > 0:

            # User wants to disable the device (leave in standby - no update)
            if poll_user[0] == 0:
                pass

            # User selected JOG function
            elif poll_user[0] == 1:
                winData1 = curses.newwin(5, 60, 5, 30)
                winData1.attron(WHITE_AND_MAGENTA)


                winData1.addstr(0, 0, "Volumetric Flow Rate Q [nL/s] in [70n, 10u] : ")
                winData1.refresh()
                win_data_ret = curses.newwin(1, 10, 5, 76)
                curses.echo()
                box = Textbox(win_data_ret)
                box.edit()
                q_user[0] = box.gather().strip().replace("\n", "")


                winData1.addstr(1, 0, "Syringe Radius in [mm] : ")
                win_data_ret.clear()
                win_data_ret.mvwin(6,55)
                winData1.refresh()
                box.edit()
                radius_user[0] = box.gather().strip().replace("\n", "")


                winData1.addstr(2, 0, "Direction ?        | FWD | REV | ? ")
                win_data_ret.clear()
                winData1.refresh()

                winData1.attroff(WHITE_AND_MAGENTA)     
                winData1.attron(WHITE_AND_GREEN)

                            # collect data
                curses.noecho()
                winData1.nodelay(True)
                q = 0
                key = ""
                while key != 'w':
                    try:
                        key = winData1.getkey()
                    except:
                        key = None

                    if key == 'a':
                        if q > 0:
                            q -= 1
                        
                    elif key == 'd':
                        if q < 1:
                            q += 1

                    winData1.attroff(WHITE_AND_GREEN)     
                    winData1.attron(WHITE_AND_MAGENTA)
                    winData1.addstr(2, 0, "Direction ?        | FWD | REV | ? ")
                    winData1.attroff(WHITE_AND_MAGENTA)     
                    winData1.attron(WHITE_AND_GREEN)

                    if q == 0:
                        winData1.addstr(2, 19, "| FWD |")
                        dir_user[0] = 1                         
                    
                    elif q == 1:
                        winData1.addstr(2, 25, "| REV |")
                        dir_user[0] = 0                    

                    winData1.refresh()
                    sleep(0.75)

            # User sel RUN function
            elif poll_user[0] == 2:

                winData1 = curses.newwin(5, 60, 5, 30)
                winData1.attron(WHITE_AND_MAGENTA)


                winData1.addstr(0, 0, "Volumetric Flow Rate Q [nL/s] in [70n, 10u] : ")
                winData1.refresh()
                win_data_ret = curses.newwin(1, 10, 5, 76)
                curses.echo()
                box = Textbox(win_data_ret)
                box.edit()
                q_user[0] = box.gather().strip().replace("\n", "")


                winData1.addstr(1, 0, "Syringe Radius in [mm] : ")
                win_data_ret.clear()
                win_data_ret.mvwin(6,55)
                winData1.refresh()
                box.edit()
                radius_user[0] = box.gather().strip().replace("\n", "")

                winData1.addstr(2, 0, "Syringe Capacity in [mL] : ")
                win_data_ret.clear()
                win_data_ret.mvwin(7,58)
                winData1.refresh()
                box.edit()
                cap_user[0] = box.gather().strip().replace("\n", "")

                winData1.addstr(3, 0, "Hour # : ")
                win_data_ret.clear()
                win_data_ret.mvwin(8,40)
                winData1.refresh()
                box.edit()
                hour_user[0] = box.gather().strip().replace("\n", "")

                winData1.addstr(3, 16, "Minute # : ")
                win_data_ret.clear()
                win_data_ret.mvwin(8,58)
                winData1.refresh()
                box.edit()
                min_user[0] = box.gather().strip().replace("\n", "")

                winData1.addstr(3, 35, "Second # : ")
                win_data_ret.clear()
                win_data_ret.mvwin(8,77)
                winData1.refresh()
                box.edit()
                sec_user[0] = box.gather().strip().replace("\n", "")


                winData1.addstr(4, 0, "Direction ?        | FWD | REV | ? ")
                win_data_ret.clear()
                winData1.refresh()

                winData1.attroff(WHITE_AND_MAGENTA)     
                winData1.attron(WHITE_AND_GREEN)

                            # collect data
                curses.noecho()
                winData1.nodelay(True)
                q = 0
                key = ""
                while key != 'w':
                    try:
                        key = winData1.getkey()
                    except:
                        key = None

                    if key == 'a':
                        if q > 0:
                            q -= 1
                        
                    elif key == 'd':
                        if q < 1:
                            q += 1

                    winData1.attroff(WHITE_AND_GREEN)     
                    winData1.attron(WHITE_AND_MAGENTA)
                    winData1.addstr(4, 0, "Direction ?        | FWD | REV | ? ")
                    winData1.attroff(WHITE_AND_MAGENTA)     
                    winData1.attron(WHITE_AND_GREEN)

                    if q == 0:
                        winData1.addstr(4, 19, "| FWD |")
                        dir_user[0] = 1                         
                    
                    elif q == 1:
                        winData1.addstr(4, 25, "| REV |")
                        dir_user[0] = 0                    

                    winData1.refresh()
                    sleep(0.5)
                

        # Act if device two is on the bus
        if rollcall[1] > 0:
            # User wants to disable the device (leave in standby - no update)
            if poll_user[1] == 0:
                pass

            # User selected JOG function
            elif poll_user[1] == 1:
                winData2 = curses.newwin(5, 60, 12, 30)
                winData2.attron(WHITE_AND_MAGENTA)


                winData2.addstr(0, 0, "Volumetric Flow Rate Q [nL/s] in [70n, 10u] : ")
                winData2.refresh()
                win_data_ret = curses.newwin(1, 10, 12, 76)
                curses.echo()
                box = Textbox(win_data_ret)
                box.edit()
                q_user[1] = box.gather().strip().replace("\n", "")


                winData2.addstr(1, 0, "Syringe Radius in [mm] : ")
                win_data_ret.clear()
                win_data_ret.mvwin(13,55)
                winData2.refresh()
                box.edit()
                radius_user[1] = box.gather().strip().replace("\n", "")


                winData2.addstr(2, 0, "Direction ?        | FWD | REV | ? ")
                win_data_ret.clear()
                winData2.refresh()

                winData2.attroff(WHITE_AND_MAGENTA)     
                winData2.attron(WHITE_AND_GREEN)

                            # collect data
                curses.noecho()
                winData2.nodelay(True)
                q = 0
                key = ""
                while key != 'w':
                    try:
                        key = winData2.getkey()
                    except:
                        key = None

                    if key == 'a':
                        if q > 0:
                            q -= 1
                        
                    elif key == 'd':
                        if q < 1:
                            q += 1

                    winData2.attroff(WHITE_AND_GREEN)     
                    winData2.attron(WHITE_AND_MAGENTA)
                    winData2.addstr(2, 0, "Direction ?        | FWD | REV | ? ")
                    winData2.attroff(WHITE_AND_MAGENTA)     
                    winData2.attron(WHITE_AND_GREEN)

                    if q == 0:
                        winData2.addstr(2, 19, "| FWD |")
                        dir_user[1] = 1                         
                    
                    elif q == 1:
                        winData2.addstr(2, 25, "| REV |")
                        dir_user[1] = 0                    

                    winData2.refresh()
                    sleep(0.75)

            # User sel RUN function
            elif poll_user[1] == 2:
                winData2 = curses.newwin(5, 60, 12, 30)
                winData2.attron(WHITE_AND_MAGENTA)


                winData2.addstr(0, 0, "Volumetric Flow Rate Q [nL/s] in [70n, 10u] : ")
                winData2.refresh()
                win_data_ret = curses.newwin(1, 10, 12, 76)
                curses.echo()
                box = Textbox(win_data_ret)
                box.edit()
                q_user[1] = box.gather().strip().replace("\n", "")


                winData2.addstr(1, 0, "Syringe Radius in [mm] : ")
                win_data_ret.clear()
                win_data_ret.mvwin(13,55)
                winData2.refresh()
                box.edit()
                radius_user[1] = box.gather().strip().replace("\n", "")

                winData2.addstr(2, 0, "Syringe Capacity in [mL] : ")
                win_data_ret.clear()
                win_data_ret.mvwin(14,58)
                winData2.refresh()
                box.edit()
                cap_user[1] = box.gather().strip().replace("\n", "")

                winData2.addstr(3, 0, "Hour # : ")
                win_data_ret.clear()
                win_data_ret.mvwin(15,40)
                winData2.refresh()
                box.edit()
                hour_user[1] = box.gather().strip().replace("\n", "")

                winData2.addstr(3, 16, "Minute # : ")
                win_data_ret.clear()
                win_data_ret.mvwin(15,58)
                winData2.refresh()
                box.edit()
                min_user[1] = box.gather().strip().replace("\n", "")

                winData2.addstr(3, 35, "Second # : ")
                win_data_ret.clear()
                win_data_ret.mvwin(15,77)
                winData2.refresh()
                box.edit()
                sec_user[1] = box.gather().strip().replace("\n", "")


                winData2.addstr(4, 0, "Direction ?        | FWD | REV | ? ")
                win_data_ret.clear()
                winData2.refresh()

                winData2.attroff(WHITE_AND_MAGENTA)     
                winData2.attron(WHITE_AND_GREEN)

                            # collect data
                curses.noecho()
                winData2.nodelay(True)
                q = 0
                key = ""
                while key != 'w':
                    try:
                        key = winData2.getkey()
                    except:
                        key = None

                    if key == 'a':
                        if q > 0:
                            q -= 1
                        
                    elif key == 'd':
                        if q < 1:
                            q += 1

                    winData2.attroff(WHITE_AND_GREEN)     
                    winData2.attron(WHITE_AND_MAGENTA)
                    winData2.addstr(4, 0, "Direction ?        | FWD | REV | ? ")
                    winData2.attroff(WHITE_AND_MAGENTA)     
                    winData2.attron(WHITE_AND_GREEN)

                    if q == 0:
                        winData2.addstr(4, 19, "| FWD |")
                        dir_user[1] = 1                         
                    
                    elif q == 1:
                        winData2.addstr(4, 25, "| REV |")
                        dir_user[1] = 0                    

                    winData2.refresh()
                    sleep(0.5)

        # Act if device three is on the bus
        if rollcall[2] > 0:
            #winData3 = curses.newwin(5, 60, 19, 30)
            # User wants to diable the device (leave in standby - no update)
            if poll_user[2] == 0:
                pass

            # User selected JOG function
            elif poll_user[2] == 1:
                winData3 = curses.newwin(5, 60, 19, 30)
                winData3.attron(WHITE_AND_MAGENTA)


                winData3.addstr(0, 0, "Volumetric Flow Rate Q [nL/s] in [70n, 10u] : ")
                winData3.refresh()
                win_data_ret = curses.newwin(1, 10, 19, 76)
                curses.echo()
                box = Textbox(win_data_ret)
                box.edit()
                q_user[2] = box.gather().strip().replace("\n", "")


                winData3.addstr(1, 0, "Syringe Radius in [mm] : ")
                win_data_ret.clear()
                win_data_ret.mvwin(20,55)
                winData3.refresh()
                box.edit()
                radius_user[2] = box.gather().strip().replace("\n", "")


                winData3.addstr(2, 0, "Direction ?        | FWD | REV | ? ")
                win_data_ret.clear()
                winData3.refresh()

                winData3.attroff(WHITE_AND_MAGENTA)     
                winData3.attron(WHITE_AND_GREEN)

                            # collect data
                curses.noecho()
                winData3.nodelay(True)
                q = 0
                key = ""
                while key != 'w':
                    try:
                        key = winData3.getkey()
                    except:
                        key = None

                    if key == 'a':
                        if q > 0:
                            q -= 1
                        
                    elif key == 'd':
                        if q < 1:
                            q += 1

                    winData3.attroff(WHITE_AND_GREEN)     
                    winData3.attron(WHITE_AND_MAGENTA)
                    winData3.addstr(2, 0, "Direction ?        | FWD | REV | ? ")
                    winData3.attroff(WHITE_AND_MAGENTA)     
                    winData3.attron(WHITE_AND_GREEN)

                    if q == 0:
                        winData3.addstr(2, 19, "| FWD |")
                        dir_user[2] = 1                         
                    
                    elif q == 1:
                        winData3.addstr(2, 25, "| REV |")
                        dir_user[2] = 0                    

                    winData3.refresh()
                    sleep(0.75)

            # User sel RUN function
            elif poll_user[2] == 2:
                winData3 = curses.newwin(5, 60, 19, 30)
                winData3.attron(WHITE_AND_MAGENTA)


                winData3.addstr(0, 0, "Volumetric Flow Rate Q [nL/s] in [70n, 10u] : ")
                winData3.refresh()
                win_data_ret = curses.newwin(1, 10, 19, 76)
                curses.echo()
                box = Textbox(win_data_ret)
                box.edit()
                q_user[2] = box.gather().strip().replace("\n", "")


                winData3.addstr(1, 0, "Syringe Radius in [mm] : ")
                win_data_ret.clear()
                win_data_ret.mvwin(20,55)
                winData3.refresh()
                box.edit()
                radius_user[2] = box.gather().strip().replace("\n", "")

                winData3.addstr(2, 0, "Syringe Capacity in [mL] : ")
                win_data_ret.clear()
                win_data_ret.mvwin(21,58)
                winData3.refresh()
                box.edit()
                cap_user[2] = box.gather().strip().replace("\n", "")

                winData3.addstr(3, 0, "Hour # : ")
                win_data_ret.clear()
                win_data_ret.mvwin(22,40)
                winData3.refresh()
                box.edit()
                hour_user[2] = box.gather().strip().replace("\n", "")

                winData3.addstr(3, 16, "Minute # : ")
                win_data_ret.clear()
                win_data_ret.mvwin(22,58)
                winData3.refresh()
                box.edit()
                min_user[2] = box.gather().strip().replace("\n", "")

                winData3.addstr(3, 35, "Second # : ")
                win_data_ret.clear()
                win_data_ret.mvwin(22,77)
                winData3.refresh()
                box.edit()
                sec_user[2] = box.gather().strip().replace("\n", "")


                winData3.addstr(4, 0, "Direction ?        | FWD | REV | ? ")
                win_data_ret.clear()
                winData3.refresh()

                winData3.attroff(WHITE_AND_MAGENTA)     
                winData3.attron(WHITE_AND_GREEN)

                            # collect data
                curses.noecho()
                winData3.nodelay(True)
                q = 0
                key = ""
                while key != 'w':
                    try:
                        key = winData3.getkey()
                    except:
                        key = None

                    if key == 'a':
                        if q > 0:
                            q -= 1
                        
                    elif key == 'd':
                        if q < 1:
                            q += 1

                    winData3.attroff(WHITE_AND_GREEN)     
                    winData3.attron(WHITE_AND_MAGENTA)
                    winData3.addstr(4, 0, "Direction ?        | FWD | REV | ? ")
                    winData3.attroff(WHITE_AND_MAGENTA)     
                    winData3.attron(WHITE_AND_GREEN)

                    if q == 0:
                        winData3.addstr(4, 19, "| FWD |")
                        dir_user[2] = 1                         
                    
                    elif q == 1:
                        winData3.addstr(4, 25, "| REV |")
                        dir_user[2] = 0                    

                    winData3.refresh()
                    sleep(0.5)

        winData4 = curses.newwin(1, 46, 25, 35)

    # JOG-RUN metrics
    elif reqGUI == RUN:
        pass

    else:
        print("Requested GUI Error")

    


wrapper(curs)



if __name__ == "__main__":
    main()
