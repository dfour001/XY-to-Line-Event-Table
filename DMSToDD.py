
def dms_to_dd(dms):
    """ Accepts coordinates in DMS format written in various ways
        and returns them in DD format.  Input should be either
        lat or lng, not both at the same time.
        Example inputs and outputs:
            37 19 09.05N  =>  37.3192
            W79-30'-16.35"  =>  -79.5045
    """

    # Check if input is already dd
    try:
        float(dms)
        return dms
    except:
        pass

    d = None
    m = None
    s = None

    WorS = False # Western or Southern Hemisphere

    ## Parse D, M, and S from input string
    # Replace everything that's not a number or . with ~
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

    # Convert dms to dd
    dd = d + m/60 + s/3600

    if WorS:
        dd = dd * -1

    return(round(dd, 4))


if __name__ == '__main__':
    input = "37°13'50.7"
    output = dms_to_dd(input)
    print(f'Input: {input}\nOutput: {output}\n')

    input = 'It will take these 46 words and turn them into 1 short DD with a very flexible input in only 2.342 milliseconds!'
    output = dms_to_dd(input)
    print(f'Input: {input}\nOutput: {output}\n')

    x = 'It will take these 46 words and turn them into 1 short DD with a very flexible input in only 2.342 milliseconds!'
    x = x.split(' ')
    print(len(x))