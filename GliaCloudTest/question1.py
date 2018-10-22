def counting(urls):
	""" return top 3 count
    :param urls: url list
    """
    url_counts = {} # record count 
    url_cache = set() # record exist or not
    for url in urls:
    	filename = url.split('/')[-1]
    	if filename not in url_cache:
    	    if filename not in url_counts:
                url_counts[filename] = 0
            else:
                url_counts[filename] += 1
            url_cache.add(filename)
    
    filename_list = sorted(data, key=url_counts.get, reverse=True)
    for i in xrange(3)
    print filename_list[i], url_counts.get(filename_list[i])

    	