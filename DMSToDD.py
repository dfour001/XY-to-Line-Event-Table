
def dms_to_dd(dms):
    """ Accepts coordinates in DMS format written in various ways
        and returns them in DD format.  Input should be either
        lat or lng, not both at the same time.
        Example inputs and outputs:
            37 19 09.05N  =>  37.3192
            W79-30'-16.35"  =>  -79.5045
    """
    WorS = False # Western or Southern Hemisphere

    # Check if hemisphere is specified as the last char
    if str(dms).strip()[-1] in ['N', 'W']:
        if dms[-1] == 'W':
            WorS = True
        dms = dms[:-1]
    
    # Check if hemisphere is specified by negative sign as the first char
    if str(dms)[0] == '-':
        WorS = True

    # Check if input is already dd
    try:
        dms = float(dms)
        if WorS and dms > 0: # If this is in DD format, should be negative, but is not
            dms = dms * -1
        
        if dms > 60: # In VA, this means it's longitude and should be negative
            dms = dms * -1

        return dms
    except:
        pass # input is not DD - proceed with conversion

    d = None
    m = None
    s = None

    

    ## Parse D, M, and S from input string
    # Replace everything that's not a number or decimal with '~'
    remove = []
    for c in dms:
        try:
            int(c)
        except:
            if c != '.':
                remove.append(c)

    for r in remove:
        dms = dms.replace(r, '~')

    # Check for hemisphere
    remove = [x.upper() for x in remove]
    if 'W' in remove or 'S' in remove:
        WorS = True
    
    # Separate numbers from ~'s
    numList = []
    dmsSplit = dms.split('~')
    for s in dmsSplit:
        try:
            float(s)
            if s != '':
                numList.append(s)
        except:
            pass
    
    try:
        d = int(numList[0])
        m = int(numList[1])
        s = float(numList[2])
    except:
        print(f'Error converteing {dms}')
        return

    if d > 60: # In VA, this means it's longitude and should be negative
        WorS = True

    # Convert dms to dd
    dd = d + m/60 + s/3600

    if WorS:
        dd = dd * -1

    return(round(dd, 7))


if __name__ == '__main__':
    # input = "37°13'50.7"
    # output = dms_to_dd(input)
    # print(f'Input: {input}\nOutput: {output}\n')

    # input = 'It will take these 22 words and turn them into 1 short DD with a very flexible input in only 2.342 milliseconds!'
    # output = dms_to_dd(input)
    # print(f'Input: {input}\nOutput: {output}\n')

    input = "79.71535"
    output = dms_to_dd(input)
    print(f'Input: {input}\nOutput: {output}\n')
    
