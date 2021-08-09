a friend asked me for help downloading some videos from his
university's portal. here's the script i used. his university uses the
yuja video service for hosting the videos. this script may have wider
utility than just downloading videos from his university.

this code is for educational purposes only. ;)

# use

you need to grab a video list json file in order to use this script.
you can do that by going to the video player and opening up the
developer console in chrome. go to the network tab, and look for a
request called 'VideoListJSON'. you can use the filter to help. save
the response json to a file, and feed that into the script.

the video list json file should look something like:
```
{
  "data": [
    {
      "videoTitle": "zoom video 1",
      "videoFileKey": "Video-12345678-1234-1234-1234-1234678abcd_processed.mp4",
      "videoFileName": zoom video 1.mp4",
      ...
    }
  ]
}
```

you also need the `ClassPID`. this appears as a query parameter on all
requests to the cloudfront domain. again, if you look at network
requests in the developer console while you're viewing videos you
should find it.

i found the only two cookies necessary are `JSESSIONID` and
`AWSALBCORS`. again, you can grab these from network requests or you
can switch to the 'Application' tab in chrome to find your cookie
values.

example of calling the script:
```
python yuja_rip.py --cookies "JSESSIONID=<JSESSIONID_VALUE>; AWSALBCORS=<AWSALBCORS_VALUE>" --class_pid 18105 --out_dir out/videos --pattern 'Video 18' video_list.json
```

# future work

it'd be great to turn this into a tool anybody with a login could use,
and skip having to monkey around w/ cookies and json blobs and such.
